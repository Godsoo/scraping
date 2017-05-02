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

brands = ['B&G', 'Garmin', 'Humminbird', 'Lowrance', 'Raymarine', 'Simrad']

def get_brand(name):
        for brand in brands:
                if brand.lower() in name.lower():
                        return brand

class WestMarineSpider(BaseSpider):
    name = 'navico-amer-westmarine.com'
    allowed_domains = ['westmarine.com']

    start_urls = ['http://www.westmarine.com']

    def start_requests(self):
        self.rows = []
        with open(os.path.join(HERE, 'navico_products.csv')) as f:
            reader = csv.DictReader(f)
            reqs = []
            for row in reader:
            	self.rows.append(row)
                url = 'http://www.westmarine.com/search?Ntt=' + row['description']
                reqs.append(Request(url, dont_filter=True, meta={'search_item': row}))

            for req in reqs:
            	yield req

        with open(os.path.join(HERE, 'west.csv')) as f:
        	reader = csv.DictReader(f)
        	for row in reader:
        		yield Request(row['url'], meta={'search_item': row})
        
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        search_item = response.meta['search_item']

        sku = ''.join(hxs.select('//span[@class="product-manufno"]/text()').extract()).strip()
        name = ''.join(hxs.select('//h1[@id="productDetailsPageTitle"]/text()').extract())
        
        for row in self.rows:
            if sku.upper() == row['code'].upper().strip() and row['brand'].upper() in name.upper().strip():
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('url', response.url)
                loader.add_value('sku', sku)
                loader.add_xpath('identifier', '//input[@name="productCodePost"]/@value')
                brand = get_brand(name) or search_item['brand']
                loader.add_value('brand', brand)
                image_url =  hxs.select('//div[@id="primary_image"]/a/img/@src').extract()
                image_url = 'http:' + image_url[0] if image_url else ''
                loader.add_value('image_url', image_url)

                category = row['category']
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
                metadata['screen_size'] = row['screen size']
                product['metadata'] = metadata
                yield product
                continue
            #else:
                #if name:
                    #log.msg('Invalid brand or code: ' + response.url)

        products = hxs.select('//div[@class="productName"]/a/@href').extract()
        for product in products:
            url = urljoin_rfc(base_url,product)
            yield Request(url, meta=response.meta)
