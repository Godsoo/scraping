import os
import csv
import cStringIO

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders import BaseAmazonSpider

class MonstersupplementsAmazonCoUkSpider(BaseAmazonSpider):
    name = 'monstersupplements-amazon.co.uk'
    all_sellers = False
    max_pages = 1

    def __init__(self, *args, **kwargs):
        super(MonstersupplementsAmazonCoUkSpider, self).__init__('www.amazon.co.uk', *args, **kwargs)

    def start_requests(self):
        with open(os.path.join(HERE, 'monstersupplements.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                yield self.search(row['name'], row)

    def match(self, search_item, new_item):
        return self.match_name(search_item, new_item) \
            and self.match_price(search_item, new_item)
