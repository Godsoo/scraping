import re
import os
import csv
from scrapy.spider import BaseSpider
from scrapy.http import Request

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class ForumSportSpider(BaseSpider):
    name = 'sportzone-forumsport.com'

    filename = os.path.join(HERE, 'sportzone_products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            url = row['forumsport.com']
            if url:
                yield Request(url, callback=self.parse_product, meta={'row': row})

    def parse_product(self, response):
        row = response.meta['row']

        image_url = response.xpath('//div[@class="product-gallery"]//img/@src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
 
        price = ''.join(response.xpath('//div[@class="model-features-card"]//div[@class="price-content"]/span[@itemprop="price"]//text()').extract())
        price = extract_price(price) if price else ''

        identifier = re.findall('identifier: "(.*)"', response.body)[0]

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('identifier', identifier)
        loader.add_value('sku', row['SKU'])
        loader.add_value('url', response.url)
        loader.add_value('image_url', image_url)
        loader.add_xpath('brand', '//div[@class="model-brand-card"]//img[@itemprop="logo"]/@title')
        loader.add_value('category', '')
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')
        loader.add_value('price', price)
        yield loader.load_item()
