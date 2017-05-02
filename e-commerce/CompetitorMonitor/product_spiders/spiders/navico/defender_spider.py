import os
import re
import json
import csv
import urlparse

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from navicoitem import NavicoMeta

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class DefenderSpider(BaseSpider):
    name = 'navico-defender.com'
    allowed_domains = ['defender.com']

    start_urls = ['http://www.defender.com/']

    def start_requests(self):
        with open(os.path.join(HERE, 'navico_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = 'http://search.defender.com/search.aspx?expression=%s&x=0&y=0' % row['code']
                yield Request(url, dont_filter=True, meta={'search_item': row})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@id="divProducts"]//tr/td/a[contains(@id, "pProductsList")]/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), dont_filter=True, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        search_item = response.meta['search_item']

        sku = ''.join(hxs.select('//span[@itemprop="model"]/text()').extract()).strip()
        name = ''.join(hxs.select('//span[@itemprop="name"]/text()').extract())
        
        if sku.upper() == search_item['code'].upper() and search_item['brand'].upper() in name.upper():
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('url', response.url)
            loader.add_value('sku', search_item['code'])
            #loader.add_xpath('identifier', '//input[@name="ProdNo1"]/@value')
            loader.add_value('brand', search_item['brand'])
            image_url =  hxs.select('//img[@itemprop="image"]/@src').extract()
            image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
            loader.add_value('image_url', image_url)

            category = search_item['category']
            if not category:
                category = hxs.select('//td[@class="whiteSmallFont"]/b/a/text()').extract()
                category = category[-1] if category else ''

            loader.add_value('category', search_item['brand'])
            loader.add_value('category', category)

            '''
            price = hxs.select('//p[contains(@class, "promo price")]/text()').extract()
            if not price:
                price =  hxs.select('//p[contains(@class, "regularPrice")]/text()').extract()
            price = extract_price(price[0]) if price else 0
            loader.add_value('price', price)
            if not price:
                loader.add_value('stock', 0)
            '''

            product = loader.load_item()
            metadata = NavicoMeta()
            metadata['screen_size'] = search_item['screen size']
            product['metadata'] = metadata

            inputs = hxs.select('//form[@action="UpdateCart"]//input')
            formdata = {}
            for input in inputs:
                formdata[''.join(input.select('@name').extract())] = ''.join(input.select('@value').extract())
            yield FormRequest("http://www.defender.com/UpdateCart", 
                              dont_filter=True, 
                              formdata=formdata, 
                              callback=self.parse_addcart,
                              meta={'item': product})
        else:
            if name:
                log.msg('Invalid brand or code: ' + response.url)

    def parse_addcart(self, response):
        hxs = HtmlXPathSelector(response)
        
        item = response.meta['item']
        products = hxs.select('//table/tr[td/input[contains(@name, "ItemId")]]')
        for product in products:
            valid_sku = item['sku'].upper() in ''.join(product.select('td[input[contains(@name, "ItemId")]]/text()').extract()).strip().upper()
            if valid_sku:
                identifier = product.select('td[input[contains(@name, "ItemId")]]/input/@value').extract()[-1]
                item['identifier'] = identifier
                price = product.select('td[@class="sellprice"]/text()').extract()
                price = extract_price(price[-1]) if price else '0'
                item['price'] = price
                yield item
                break
