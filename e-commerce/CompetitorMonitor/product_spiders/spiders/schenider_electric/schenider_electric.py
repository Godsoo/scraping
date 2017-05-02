import os
import csv
from w3lib.url import url_query_parameter
from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class SchneiderElectric(BaseSpider):
    name = 'schenider_electric-schneider-electric.co.uk'

    filename = os.path.join(HERE, 'products.csv')
    start_urls = ('file://' + filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['SKU Code'])
            loader.add_value('sku', row['SKU Code'])
            loader.add_value('name', row['Name'].decode('utf8'))
            loader.add_value('price', row['Price'])
            loader.add_value('brand', row['Brand'])
            loader.add_value('category', row['Category'])
            loader.add_value('url', row['Your Own URL'])
            yield Request(url_query_parameter(row['Your Own URL'], 'p_url'),
                          self.parse_product, 
                          meta={'loader': loader})
            
    def parse_product(self, response):
        loader = response.meta['loader']
        image_url = response.xpath('//img[@id="productImage"]/@src').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        yield loader.load_item()
