# -*- coding: utf-8 -*-
import os.path
import re
import csv

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


HERE = os.path.abspath(os.path.dirname(__file__))

class BuckandhickmanComSpider(PrimarySpider):
    name = 'buckandhickman.com'
    allowed_domains = ['buckandhickman.com']
    start_urls = ('http://www.buckandhickman.com/find/category-is-AB+Abrasives',)

    csv_file = 'buckandhickman_crawl.csv'

    def __init__(self, *args, **kwargs):
        super(BuckandhickmanComSpider, self).__init__(*args, **kwargs)

        self.codes = {}

        with open(os.path.join(HERE, 'competitors_codes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.codes[row['url'].lower()] = row['code']

    def parse(self, response):
        base_url = get_base_url(response)
        categories_urls = response.xpath('//ul[@class="menu"]//a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        # lookup for subcategories
        categories_urls = response.xpath('//ul[@class="submenu"]//a/@href').extract()
        for url in categories_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)
        # pagination
        pages_urls = response.xpath('//ul[@class="pages"]/li/a/@href').extract()
        for url in pages_urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

        # parse products list
        try:
            category = response.xpath('//*[@id="breadcrumbs"]/li[5]/a/text()').extract()[0]
        except IndexError:
            retry = response.meta.get('retry', 0)
            if retry < 10:
                meta = response.meta.copy()
                meta['retry'] = retry + 1
                yield Request(response.url,
                              dont_filter=True,
                              meta=meta,
                              callback=self.parse_category)
                return
            else:
                category = None
        rows = response.xpath('//*[@id="content"]//table[contains(@class, "product-list-table")]/tbody//tr[@class="more-info"]')
        for row in rows:
            product_loader = ProductLoader(item=Product(), response=response)
            if row:
                try:
                    url = row.xpath('./td[@class="thumbnail"]/a/@href').extract()[0]
                    sku = row.xpath('./td/ul/li[span[contains(text(), "Part Number")]]/text()').extract()[-1].strip()
                except:
                    continue

                product_loader.add_value('sku', sku)

                url = urljoin_rfc(base_url, url)
                product_loader.add_value('url', url)
                image_url = row.xpath('./td[@class="thumbnail"]/a/img/@src').extract()[0]
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url))

                brand = row.xpath('./td/ul/li[span[contains(text(), "Manufacturer")]]/text()').extract()[-1].strip()
                product_loader.add_value('brand', brand)

                product_name = row.xpath('./td[@class="thumbnail"]/a/img/@alt').extract()[0]

                brand_in_name = False
                for w in re.findall('([a-zA-Z]+)', product_name):
                    if w.upper() in brand.upper():
                        brand_in_name = True

                if brand.upper() not in product_name.upper() and 'NONE' not in brand.upper() and not brand_in_name:
                    product_name = brand + ' ' + product_name

                product_loader.add_value('name', product_name)
                identifier = row.xpath('./td/ul/li[span[contains(text(), "Order Code")]]/text()').extract()[-1].strip()
                product_loader.add_value('identifier', identifier)
                stock_text = row.xpath('./td[5]/text()').extract()[0]
                add_button = row.xpath('./td//div[@class="basket-btn"]/input[@value="Add to Basket"]')
                if add_button:
                    product_loader.add_value('stock', 1)
                # try:
                #     stock = int(stock_text.replace('Stocked Item:', '').strip())
                # except ValueError:
                #     stock = 0
                # The client would like if the level is set to 0 and it also has a green tick, to mark it as in stock.
                # if stock:
                #     product_loader.add_value('stock', stock)
                #elif 'No Longer Manufactured' in stock_text:
                    # Product delisted
                #    continue
                price = row.xpath('./td/div[contains(@class, "price")]/p/text()').extract()[-1].strip()
                product_loader.add_value('price', extract_price(price))

                if category:
                    product_loader.add_value('category', category)
                product = product_loader.load_item()
                yield product
