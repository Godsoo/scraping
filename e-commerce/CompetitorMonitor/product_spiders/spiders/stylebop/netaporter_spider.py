import os
import csv
import re

import shutil

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))

class NetAPorterSpider(BaseSpider):
    name = 'stylebop-net-a-porter.com'
    allowed_domains = ['net-a-porter.com']
    start_urls = ('http://www.net-a-porter.com',)
    errors = []

    def start_requests(self):
        params = {'channel': 'AM',
                  'country': 'US',
                  'httpsRedirect': '',
                  'language': 'en',
                  'redirect': ''}

        req = FormRequest(url="http://www.net-a-porter.com/intl/changecountry.nap?overlay=true", formdata=params)
        yield req

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[not(contains(a/text(), "Designers"))]/div[@class="dd-menu"]/../a/@href').extract()

        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        products = hxs.select('//div[@class="description"]/a/@href').extract()
        for product in products:
            category = (hxs.select('//div[@class="product-list-title"]/h1/a/text()').extract() or 
                        hxs.select('//div[@class="product-list-title"]/h1/text()').extract()).pop()
            url = urljoin_rfc(base_url, product)
            meta['category'] = category
            yield Request(url, callback=self.parse_product, meta=meta)

        next = hxs.select('//div[@class="page-numbers "]/a[@class="next-page"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_category)

    def parse_dvf(self, response):
        if "DVF MADE FOR GLASS" not in response.body:
            return False
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        name = hxs.select('//div[@class="description"]/text()').extract().pop().strip()
        brand = "DVF"
        meta = response.meta
        identifier = hxs.select('//input[@id="productId" and @value!=""]/@value').extract()
        url = meta.get('url') if meta.get('url', None) else response.url
        sku = meta.get('sku', None)
        if not identifier:
            identifier = hxs.select('//*[@itemprop="sku"]/@content').extract()
        if not identifier:
            identifier = re.findall("product/([^/]*)/", url)

        if identifier:
            identifier = identifier[0]

        if not sku:
            sku = hxs.select('//meta[@itemprop="sku"]/@content').extract()
            sku = sku[0] if sku else ''
        brand = meta.get('brand') if meta.get('brand', None) else brand
        image_url = hxs.select('//div[@class="product-image"]/img/@src').extract()
        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if price:
            price = extract_price(price[0])
        else:
            price = 0

        l = ProductLoader(item=Product(), response=response)
        l.add_value('name', brand + ' ' + name)
        l.add_value('url', url)
        l.add_value('identifier', identifier)
        l.add_value('sku', sku)
        l.add_value('brand', brand)
        if image_url:
            l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        l.add_value('category', meta.get('category'))
        l.add_value('price', price)
        return l.load_item()

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta
  
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        if not name:
            item = self.parse_dvf(response)
            if not item:
                self.errors.append("Name not found on " + response.url)
            else:
                yield item
            return

        l = ProductLoader(item=Product(), response=response)

        brand = hxs.select('//h2[@itemprop="brand"]/a/text()').extract()[0]
        l.add_value('name', brand + ' ' + name.pop())

        url = meta.get('url') if meta.get('url', None) else response.url
        l.add_value('url', url)

        identifier = hxs.select('//input[@id="productId" and @value!=""]/@value').extract()
        if not identifier:
            identifier = hxs.select('//*[@itemprop="sku"]/@content').extract()
        if not identifier:
            identifier = re.findall("product/([^/]*)/", url)

        if identifier:
            identifier = identifier[0]
        l.add_value('identifier', identifier)

        sku = meta.get('sku', None)
        if not sku:
            sku = hxs.select('//meta[@itemprop="sku"]/@content').extract()
            sku = sku[0] if sku else ''
        l.add_value('sku', sku)

        brand = meta.get('brand') if meta.get('brand', None) else brand
        l.add_value('brand', brand)

        image_url = hxs.select('//img[@id="medium-image"]/@src').extract()
        if image_url:
            l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        l.add_value('category', meta.get('category'))
        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if price:
            price = extract_price(price[0])
        else:
            price = 0
        l.add_value('price', price)

        out_of_stock = hxs.select('//div[@class="sold-out-message"]/span/text()').extract()
        if out_of_stock:
            l.add_value('stock', 0)

        yield l.load_item()

        colors = hxs.select('//div[@id="alternative-colors"]/a/@href').extract()
        for color in colors:
            yield Request(urljoin_rfc(base_url, color[0]), callback=self.parse_product)
