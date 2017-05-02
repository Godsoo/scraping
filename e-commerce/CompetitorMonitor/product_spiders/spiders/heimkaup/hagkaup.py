import os
import re
import json
import csv
import urlparse

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from heimkaupitems import HeimkaupProduct as Product

HERE = os.path.abspath(os.path.dirname(__file__))

class HagkaupSpider(BaseSpider):
    name = 'heimkaup-hagkaup.is'
    allowed_domains = ['hagkaup.is']

    start_urls = ['http://hagkaup.is/vorur']

    def __init__(self, *args, **kwargs):
        super(HagkaupSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="snav"]//ul[@class="level1"]/li/a/@href').extract()
        categories = list(set(categories))
        categories += hxs.select('//div[@class="products milli"]//h3/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcategories = hxs.select('//div[@class="products milli"]//h3/a/@href').extract()
        for url in subcategories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_subcategories)

        next_page = hxs.select('//a[@class="next ajaxLoadpage"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_subcategories)

        products = hxs.select('//div[contains(@class,"products box")]//h3/a/@href').extract()
        for url in set(products):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select('//div[@class="boxbody"]/h1/text()[normalize-space()]').extract()
        if not product_name:
            retried = response.meta.get('retried', False)
            if not retried:
                yield Request(response.url, dont_filter=True, meta={'retried': True}, callback=self.parse_product)


        product_price = hxs.select('//div[@class="price"]/ins/b/text()').extract()
        product_price = product_price[0] if product_price else None

        if not product_price:
            product_price = re.search('Price=(.*)', response.body)
            if product_price:
                product_price = product_price.group(1).replace('.', '')
            else:
                retried = response.meta.get('retried', False)
                if not retried:
                    yield Request(response.url, dont_filter=True, meta={'retried': True}, callback=self.parse_product)

        image_url = hxs.select('//a[@class="img"]/@href').extract()
        out_of_stock = hxs.select('//li[@class="serpontunactive"]')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@class="boxbody"]/h1/text()[normalize-space()]')
        loader.add_value('url', response.url)
        loader.add_xpath('sku', '//*', re=r'ProductNo=(.*)')
        loader.add_xpath('identifier', '//*', re=r'ProductID=(.*)')
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_xpath('category', '//li[@class="current"]/a/text()', lambda e: e[0] if e else '')
        product_price = extract_price(product_price.replace('.', '').replace(',', '.'))
        loader.add_value('price', product_price)
        loader.add_xpath('brand', '//*', lambda e: e[0] if e else '', re=r'Trademark=(.*)')

        item = loader.load_item()

        if not item.get('sku') or not item.get('name'):
            retried = response.meta.get('retried', False)
            if not retried:
                yield Request(response.url, dont_filter=True, meta={'retried': True}, callback=self.parse_product)
                return

        if not item.get('price'):
            item['stock'] = 0

        yield item
