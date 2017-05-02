import os
import csv
from cStringIO import StringIO

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.items import Product, \
    ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import extract_price

from schenideritems import ScheniderMeta

HERE = os.path.abspath(os.path.dirname(__file__))

from scrapy import log


class ScrewfixSpider(BaseSpider):
    name = 'schenider_electric-screwfix.com'
    allowed_domains = ['screwfix.com']

    start_urls = ['http://www.screwfix.com']


    def parse(self, response):
        url = "http://www.screwfix.com/jsp/account/ajax/switchIncExVat.jsp"
        
        yield Request(url, callback=self.parse_exc_vat) 

    def parse_exc_vat(self, response):
        yield Request('http://www.screwfix.com/', dont_filter=True, callback=self.parse_products) 

    def parse_products(self, response):
        filename = os.path.join(HERE, 'trial_skus.csv')
        with open(filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'http' in row['Screwfix']:
                    yield Request(row['Screwfix'], callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):

        row = response.meta['row']

        categories = response.xpath('//div[contains(@class, "breadcrumb")]//li/a[@class="bc__link bc__link--last"]/span/text()').extract()
        if categories:
            category = categories[0].strip()

        price = ''.join(response.xpath('//div[@id="product_price"]//text()').extract()).strip()
        if not price:
            price = response.xpath('//span[@itemprop="price"]/text()').re(r'[\d.,]+')[0]

        price = extract_price(price)

        brand = response.xpath('//img[@id="product_brand_img"]/@alt').extract()
        brand = brand[0] if brand else ''

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//span[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_xpath('identifier', '//span[@itemprop="productID"]/text()')
        loader.add_value('sku', row['Reference'])
        loader.add_xpath('image_url', "//img[@itemprop='image']/@src")
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        loader.add_value('category', category)
        loader.add_value('brand', brand)

        delivery = response.xpath('.//button[contains(@id, "product_add_to_trolley") and contains(@title, "delivery")]')
        collection = response.xpath('.//button[contains(@id, "add_for_collection_button_")]')

        if not delivery and not collection:
            loader.add_value('stock', 0)

        item = loader.load_item()

        metadata = ScheniderMeta()
        metadata['name'] = item['name']
        metadata['brand'] = item['brand']
        item['metadata'] = metadata

        yield item
