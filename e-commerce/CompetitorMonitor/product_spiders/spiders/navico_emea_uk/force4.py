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

from navicoitems import NavicoMeta

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class Force4Spider(BaseSpider):
    name = 'navico-force4.co.uk'
    allowed_domains = ['force4.co.uk']

    force4_products = {}

    start_urls = []

    def start_requests(self):

        with open(HERE+'/force4_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.force4_products[row['Code'].strip().upper()] = row['Screen Size']

        brands = [{'name': "B&G",
                   'url': 'http://www.force4.co.uk/department/brands/b-g.html?limit=all'},
                  {'name': "Lowrance",
                   'url': 'http://www.force4.co.uk/department/brands/lowrance.html?limit=all'},
                  {'name': "Raymarine",
                   'url': 'http://www.force4.co.uk/department/brands/raymarine.html?limit=all'},
                  {'name': "Garmin",
                   'url': 'http://www.force4.co.uk/department/brands/garmin.html?limit=all'},
                  {'name': "Simrad",
                   'url': 'http://www.force4.co.uk/department/brands/simrad.html?limit=all'},
                  {'name': "Humminbird",
                   'url': 'http://www.force4.co.uk/department/brands/humminbird.html?limit=all'}]
        for brand in brands:
            yield Request(brand['url'], meta={'brand': brand['name']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select('//div[@class="product-name"]/h1/text()')[0].extract()
        product_price = hxs.select('//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not product_price:
            product_price = hxs.select('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        if product_price:
            product_price = product_price[0]
        product_code = hxs.select('//div[@class="product-code"]/text()').re('Product code: (.*)')[0]
        image_url = hxs.select('//img[@class="product-img-img"]/@src').extract()
        brand = response.meta.get('brand', '')
        category = brand
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_value('category', category)
        product_price = extract_price(product_price)
        loader.add_value('price', product_price)
        if not product_price:
            loader.add_value('stock', 0)

        product = loader.load_item()
        metadata = NavicoMeta()
        metadata['screen_size'] = self.force4_products.get(product_code.strip().upper(), '')
        product['metadata'] = metadata

        yield product
