import os
import csv
from scrapy.spider import BaseSpider
from scrapy.http import Request

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class SportZoneSpider(BaseSpider):
    name = 'sportzone-sportzone.es'

    filename = os.path.join(HERE, 'sportzone_products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            yield Request(row['URL'], callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        row = response.meta['row']

        name = ' '.join(response.xpath('//div[@class="product-title"]//text()').extract()).strip()
        colour = response.xpath('//div[@class="product-colors__header"]//span[@class="current"]/text()').extract()
        if colour:
            name += ' ' + colour[0].strip()

        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        image_url = image_url[0] if image_url else ''
 
        price = response.xpath('//p[@class="product-price__now"]/span[@class="value"]/text()').extract()
        price = extract_price(price[0]) if price else ''

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', row['SKU'])
        loader.add_value('sku', row['SKU'])
        loader.add_value('url', response.url)
        loader.add_value('image_url', image_url)
        loader.add_xpath('brand', '//meta[@property="og:brand"]/@content')
        categories = response.xpath('//ul[@class="breadcrumbs"]//a/text()').extract()[-3:]
        loader.add_value('category', categories)
        loader.add_value('name', name)
        loader.add_value('price', price)
        yield loader.load_item()
