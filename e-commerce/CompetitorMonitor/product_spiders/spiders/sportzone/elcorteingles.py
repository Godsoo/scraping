import os
import csv
from scrapy.spider import BaseSpider
from scrapy.http import Request

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class ElCorteInglesSpider(BaseSpider):
    name = 'sportzone-elcorteingles.es'

    filename = os.path.join(HERE, 'sportzone_products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            url = row['elcorteingles.es']
            if url:
                yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        row = response.meta['row']

        name = response.xpath('//h2[@itemprop="name"]/text()').extract()[0].strip()
        colour = response.xpath('//p[@class="common-option variant-ctrl"]/text()').extract()
        if colour:
            name += ' ' + colour[0].strip()

        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        image_url = 'http:' + image_url[0] if image_url else ''
 
        price = ''.join(response.xpath('//div[contains(@class, "product-price")]/span[contains(@class, "current")]//text()').extract())
        price = extract_price(price) if price else ''

        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('identifier', '//div[@id="pid"]/@data-product-id')
        loader.add_value('sku', row['SKU'])
        loader.add_value('url', response.url)
        loader.add_value('image_url', image_url)
        loader.add_xpath('brand', '//h2[@itemprop="brand"]/a/text()')
        categories = response.xpath('//ul[@id="breadcrumbs"]//span/text()').extract()
        loader.add_value('category', categories)
        loader.add_value('name', name)
        loader.add_value('price', price)
        yield loader.load_item()
