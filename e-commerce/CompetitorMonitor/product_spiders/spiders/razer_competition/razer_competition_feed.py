import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
import csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class RazerCompFeedSpider(BaseSpider):
    name = 'razer-competition-feed.com'
    allowed_domains = ['razerzone.com']
    start_urls = ('http://www.razerzone.com/',)

    def parse(self, response):
        f = open(os.path.join(HERE, 'razer_competition_feed.csv'))
        reader = csv.DictReader(f)
        for row in reader:
            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector())
            loader.add_value('name', row['CLIENT PRODUCT'])
            loader.add_value('identifier', row['SKU'])
            loader.add_value('sku', row['SKU'])
            loader.add_value('brand', row['BRAND'])
            loader.add_value('price', row['PRICE'])
            loader.add_value('category', row['CATEGORY'])
            loader.add_value('image_url', row['IMAGE'])
            yield loader.load_item()