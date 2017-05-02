import os
import csv
import StringIO

from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class BablasSpider(BaseSpider):
    name = 'bablas.co.uk'
    allowed_domains = ['bablas.co.uk']
    start_urls = ('http://www.bablas.co.uk/media/feed/bablas_gb.txt',)

    def __init__(self, *args, **kwargs):
        super(BablasSpider, self).__init__(*args, **kwargs)
        self._brands = {}
        with open(os.path.join(HERE, 'brands.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._brands[row['id'].lower()] = row['brand']

    def parse(self, response):
        f = StringIO.StringIO(response.body)
        rows = csv.DictReader(f, delimiter='\t')
        for row in rows:
            if row['brand'].strip():
                brand = row['brand']
            else:
                brand = self._brands.get(row['id'].lower())
            out_of_stock = False
            availability = row.get('availability', '')
            if availability:
                if availability.lower() == 'out of stock':
                    out_of_stock = True

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('url', row['link'])
            loader.add_value('name', row['title'].decode('utf-8'))
            loader.add_value('price', row['price'])
            loader.add_value('image_url', row['image_link'])
            loader.add_value('identifier', row['id'].lower())
            if out_of_stock:
                loader.add_value('stock', 0)
            loader.add_value('sku', row['id'])
            loader.add_value('category', row['google_product_category'])
            loader.add_value('brand', brand)
            product = loader.load_item()
            product['sku'] = product['sku'].upper()
            yield product
