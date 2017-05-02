import csv
import os

from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


from bricomanitems import BricomanMeta

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class BricomanSpider(BaseSpider):
    name = 'newbricoman-bricoman.it'
    allowed_domains = ['bricoman.it']
    start_urls = ('http://www.bricoman.it',)

    def parse(self, response):
        '''
        Dummy spider for Bricoman site.
        The image_url field wasn't provided by the client,
        In case of an update, we will need to extract the images 
        from each product page using the urls in the flat file.
        '''
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                loader = ProductLoader(item=Product(), response=response)
                # loader.add_value('sku', row['Code'])
                if row['model']:
                    loader.add_value('sku', unicode(row['model'], errors='ignore'))
                else:
                    loader.add_value('sku', row['EAN'])
                loader.add_value('identifier', row['EAN'])
                loader.add_value('name', unicode(row['Web description'], errors='ignore'))
                loader.add_value('category', row['category'])
                loader.add_value('brand', unicode(row['Brand'], errors='ignore'))
                loader.add_value('price', row['price'])
                loader.add_value('url', row['url'])
                loader.add_value('image_url', row.get('image_url', ''))

                product = loader.load_item()
                metadata = BricomanMeta()
                metadata['ean'] = row['EAN']
                metadata['code'] = row['Code']
                metadata['model'] = row['model']
                product['metadata'] = metadata

                yield product
