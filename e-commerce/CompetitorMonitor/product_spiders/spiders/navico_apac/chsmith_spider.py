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

from product_spiders.spiders.navico_amer.navicoitem import NavicoMeta

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class CHSmithSpider(BaseSpider):
    name = 'navico-apac-chsmith.com.au'
    allowed_domains = ['chsmith.com.au']

    start_urls = ['http://www.chsmith.com.au']

    def start_requests(self):
        with open(os.path.join(HERE, 'navico_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = 'http://www.chsmith.com.au/catalogsearch/result/?q=' + row['code']
                yield Request(url, dont_filter=True, meta={'search_item': row})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//li[contains(@class, "item")]/a/@href').extract()
        for product in products:
            yield Request(product, dont_filter=True, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        search_item = response.meta['search_item']

        brand = ''.join(hxs.select('//tr[contains(th/h2/text(), "Brand")]/td/a/span/text()').extract())
        products = hxs.select('//tr[@class="magazinProductTableRowData"]')
        for product in products:
            try:
                name, sku = product.select('td/a[contains(b/text(), "MPN")]/text()').extract()
            except:
                continue
            if sku.upper() == search_item['code'].upper() and search_item['brand'].upper() == brand.upper():
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('name', name)
                loader.add_value('url', response.url)
                loader.add_value('sku', search_item['code'])
                loader.add_xpath('identifier', '@id')
                loader.add_value('brand', search_item['brand'])
                image_url = hxs.select('//div[@class="product-img-box"]/a/img/@src').extract()
                image_url = image_url[0] if image_url else ''
                loader.add_value('image_url', image_url)

                category = search_item['category']
                if not category:
                    category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
                    category = category[-1].strip() if category else ''
 
                loader.add_value('category', search_item['brand'])
                loader.add_value('category', category)
  
                price = product.select('td[contains(text(), "$")]/a/text()').extract()
                price = extract_price(price[0]) if price else 0
                loader.add_value('price', price)
                in_stock = product.select('td[contains(a/text(), "In Stock")]/a/text()').extract()
                if not in_stock:
                    loader.add_value('stock', 0)

                product = loader.load_item()
                metadata = NavicoMeta()
                metadata['screen_size'] = search_item['screen size']
                product['metadata'] = metadata
                yield product
