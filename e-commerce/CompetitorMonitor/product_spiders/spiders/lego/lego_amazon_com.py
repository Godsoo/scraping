import os
import csv
import cStringIO

from utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders import BaseAmazonSpider

class MonstersupplementsAmazonCoUkSpider(BaseAmazonSpider):
    name = 'lego-amazon.com-new'

    def __init__(self, *args, **kwargs):
        super(MonstersupplementsAmazonCoUkSpider, self).__init__('www.amazon.com', *args, **kwargs)

    def start_requests(self):
        with open(os.path.join(HERE, 'lego.csv')) as f:
            reader = csv.reader(cStringIO.StringIO(f.read()))
            for row in reader:
                yield self.search('LEGO ' + row[2], {
                        'sku': row[2],
                        'name': row[3],
                        'price': extract_price(row[4]),
                        })

    def collect(self, collected_items, new_item):
        return self.collect_all(collected_items, new_item)

    def match(self, search_item, new_item):
        return self.match_name(search_item, new_item) \
            and (new_item['brand'].upper() == 'LEGO' or new_item['brand'].startswith('LEGO '))

