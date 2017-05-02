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

from navicoitem import NavicoMeta

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class WestMarineSpider(BaseSpider):
    name = 'navico-westmarine.com'
    allowed_domains = ['westmarine.com']

    start_urls = ['http://www.westmarine.com']

    def start_requests(self):
        with open(os.path.join(HERE, 'navico_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = 'http://www.westmarine.com/search?text=' + row['code']
                yield Request(url, dont_filter=True, meta={'search_item': row})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        search_item = response.meta['search_item']

        sku = ''.join(hxs.select('//span[@class="product-manufno"]/text()').extract()).strip()
        name = ''.join(hxs.select('//h1[@id="productDetailsPageTitle"]/text()').extract())
        
        if sku.upper() == search_item['code'].upper() and search_item['brand'].upper() in name.upper():
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('url', response.url)
            loader.add_value('sku', search_item['code'])
            loader.add_xpath('identifier', '//input[@name="productCodePost"]/@value')
            loader.add_value('brand', search_item['brand'])
            image_url =  hxs.select('//div[@id="primary_image"]/a/img/@src').extract()
            image_url = 'http:' + image_url[0] if image_url else ''
            loader.add_value('image_url', image_url)

            category = search_item['category']
            if not category:
                category = hxs.select('//div[@id="breadcrumb"]/ul/li/a/text()').extract()
                category = category[-1] if category else ''

            loader.add_value('category', search_item['brand'])
            loader.add_value('category', category)

            price = hxs.select('//p[contains(@class, "promo price")]/text()').extract()
            if not price:
                price =  hxs.select('//p[contains(@class, "regularPrice")]/text()').extract()
            price = extract_price(price[0]) if price else 0
            loader.add_value('price', price)
            if not price:
                loader.add_value('stock', 0)

            product = loader.load_item()
            metadata = NavicoMeta()
            metadata['screen_size'] = search_item['screen size']
            product['metadata'] = metadata
            yield product
        else:
            if name:
                log.msg('Invalid brand or code: ' + response.url)
