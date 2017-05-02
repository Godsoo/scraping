import csv
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoader
from scrapy.http import Request


class ElefantFeedSpider(BaseSpider):
    name = 'elefant_ro_feed'
    allowed_domains = ['www.elefant.ro']
    start_urls = ('http://www.elefant.ro/feeds/fact-finder-carti.csv',)

    def parse(self, response):
        csv_file = csv.StringIO(response.body)

        for row in csv.reader(csv_file):
            meta = {}
            loader = ProductLoader(item=Product(), selector="")
            loader.add_value('identifier', row[0])
            loader.add_value('name', row[1].decode('iso-8859-15'))
            author = row[3].decode('iso-8859-15')
            loader.add_value('price', row[4] or '0')
            loader.add_value('category', row[5].decode('iso-8859-15'))
            loader.add_value('category', row[6].decode('iso-8859-15'))
            loader.add_value('url', row[8])
            loader.add_value('image_url', row[9])
            publisher = row[12].decode('iso-8859-15')
            loader.add_value('sku', row[21].decode('iso-8859-15'))
            loader.add_value('brand', publisher)
            product = loader.load_item()

            if author:
                meta['author'] = author
            if publisher:
                meta['publisher'] = publisher

            product['metadata'] = meta
            yield product
