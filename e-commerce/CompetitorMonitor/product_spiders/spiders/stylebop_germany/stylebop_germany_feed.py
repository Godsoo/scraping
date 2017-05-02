import os
import csv
import StringIO
from scrapy.spider import BaseSpider

from scrapy.http import Request

from utils import extract_price_eu as extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class StyleBopSpider(BaseSpider):
    name = 'stylebop-germany-stylebop.com'
    allowed_domains = ['stylebop.com']
    start_urls = ('http://www.stylebop.com/changeCountry.php?page=setDir&countryId=3&x=9&y=10',)

    

    def parse(self, response):
        yield Request('http://www.stylebop.com/export/tracking_pilot/de.csv', callback=self.parse_feed)

    def parse_feed(self, response):
        reader = csv.DictReader(StringIO.StringIO(response.body), delimiter='\t')
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['id'].lower())
            #loader.add_value('sku', row['id'].lower())
            loader.add_value('brand',  unicode(row['brand'], errors='ignore'))
            loader.add_value('category',  unicode(row['category'], errors='ignore'))
            loader.add_value('name',  unicode(row['name'], errors='ignore'))
            loader.add_value('price', row['price'])
            loader.add_value('url', row['url'])
            loader.add_value('image_url', row['image'])
            yield loader.load_item()
