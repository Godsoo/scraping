"""
Account: Camelbak DE
Name: camelbak-de-bike24.com

IMPORTANT!!

- This spider is blocked, please be careful, the website bans the proxies FOREVER!! and we can't use those there anymore.


TODO:

- Create Bike24 Base Spider, three spiders at the moment crawling this website:

  1. This (camelbak-de-bike24.com)
  2. zyro-bike24.com (Zyro account)
  3. crc-de-bike24.com (CRC DE account)

"""


import os
import csv
from cStringIO import StringIO
from datetime import datetime
from scrapy.spiders import Request
from scrapy.spiders import Rule, CrawlSpider as Spider
from scrapy.linkextractors import LinkExtractor
from scrapy.utils.url import url_query_cleaner
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.contrib.compmon2 import Compmon2API
from product_spiders.config import (
    new_system_api_roots as API_ROOTS,
    api_key as API_KEY,
    DATA_DIR,
)


class Bike24Spider(Spider):
    name = 'camelbak-de-bike24.com'
    allowed_domains = ['bike24.com']

    start_urls = ['https://www.bike24.com/manufacturers/Camelbak.html']
    rules = [Rule(LinkExtractor(allow='/p\d+\.html'), callback='parse_product')]

    rotate_agent = True

    full_run_day = 12

    def __init__(self, *args, **kwargs):
        super(Bike24Spider, self).__init__(*args, **kwargs)

        self.data_copied = False
        self.id_seen = []
        self.full_run = datetime.today().day == self.full_run_day
        if not self.full_run:
            dispatcher.connect(self.copy_previous_data, signals.spider_idle)

    def start_requests(self):
        if self.full_run:
            for req in self.start_full():
                yield req
        else:
            for req in self.start_simple():
                yield req

    def start_full(self):
        for req in list(super(Bike24Spider, self).start_requests()):
            yield req

    def start_simple(self):
        cm_api = Compmon2API(API_ROOTS['new_system'], API_KEY)
        matched_products = cm_api.get_matched_products(self.website_id)
        self.matched_ids = set()
        for m in matched_products:
            yield Request(m['url'], callback=self.parse_product)

    def copy_previous_data(self, *args, **kwargs):
        if not self.data_copied:
            self.data_copied = True
            if hasattr(self, 'prev_crawl_id'):
                products_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
                if os.path.exists(products_filename):
                    req = Request('file://' + products_filename,
                                  callback=self.parse_previous_crawl)
                    self.crawler.engine.crawl(req, self)

    def parse_previous_crawl(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            if row['identifier'] not in self.id_seen:
                self.id_seen.append(row['identifier'])

                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', row['identifier'].decode('utf-8'))
                loader.add_value('sku', row['sku'].decode('utf-8'))
                loader.add_value('name', row['name'].decode('utf-8'))
                loader.add_value('price', row['price'])
                loader.add_value('url', row['url'].decode('utf-8'))
                loader.add_value('category', row['category'].decode('utf-8'))
                loader.add_value('brand', row['brand'].decode('utf-8'))
                loader.add_value('image_url', row['image_url'].decode('utf-8'))
                if row['stock']:
                    loader.add_value('stock', int(row['stock']))
                yield loader.load_item()

    def parse_product(self, response):
        identifier = response.xpath('//form[@id="pdAddToCart"]//input[@name="product"]/@value').extract()
        if not identifier:
            return

        loader = ProductLoader(item=Product(), response=response)
        # Normalize URL
        product_url = url_query_cleaner(response.url, parameterlist=('content', 'product'), sep=';')
        loader.add_value('url', product_url)
        loader.add_value('identifier', identifier)
        sku = response.xpath('//table[@class="table-bordered table-striped table-product-datasheet"]'
                             '//td[text()="Item Code:"]/following-sibling::td[1]/text()').extract()
        if sku:
            loader.add_value('sku', sku[0])
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')

        price = response.xpath('//div[@class="box-price js-price"]/span[@itemprop="price"]/text()').extract()
        if price:
            price = extract_price(price[0].strip().replace('.','').replace(',','.'))
            loader.add_value('price', price)
        else:
            loader.add_value('price', '0.0')

        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        brand = response.xpath('//table[@class="table-bordered table-striped table-product-datasheet"]'
                               '//td[text()="Manufacturer:"]/following-sibling::td[1]/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])

        category = response.xpath('//ul[@class="nav"]//li[contains(@class,"item-active")]/a/text()').extract()
        if category:
            loader.add_value('category', category)

        availability = response.xpath('//*[@id="js-availability-label"]/text()').extract()
        if availability and 'unknown' in availability[0].lower():
            loader.add_value('stock', 0)

        product = loader.load_item()
        options = response.xpath('//div[@class="input-group input-group-select"]/select')
        if not options:
            if not (getattr(self, 'simple_run', False) and (hasattr(self, 'matched_identifiers')) \
               and (product['identifier'] not in self.matched_identifiers)):

                if not product['identifier'] in self.id_seen:
                    self.id_seen.append(product['identifier'])
                    yield product

            return

        for sel in options:
            opt = ''
            select_name = sel.xpath('@name').extract()
            if select_name:
                opt = select_name[0].replace('opt_','')
            for option in sel.xpath('option[@value!="-2"]'):
                item = Product(product)
                opt_id = option.xpath('@value').extract()
                if opt_id:
                    item['identifier'] += '-' + opt + '-' + opt_id[0]
                    item['stock'] = 1
                    opt_stock = option.xpath('@data-av').extract()
                    if opt_stock and opt_stock[0] == '100':
                        item['stock'] = 0
                    opt_name = option.xpath('text()').extract()
                    if opt_name:
                        item['name'] += ' - ' + opt_name[0]

                    if getattr(self, 'simple_run', False) and (hasattr(self, 'matched_identifiers')) \
                       and (item['identifier'] not in self.matched_identifiers):
                        continue

                    if not item['identifier'] in self.id_seen:
                        self.id_seen.append(item['identifier'])
                        yield item

    def closing_parse_simple(self, response):
        for item in super(Bike24Spider, self).closing_parse_simple(response):
            if isinstance(item, Product):
                if 'shipping_cost' in item:
                    del item['shipping_cost']
                # Normalize URL
                item['url'] = url_query_cleaner(item['url'], parameterlist=('content', 'product'), sep=';')
            yield item
 
