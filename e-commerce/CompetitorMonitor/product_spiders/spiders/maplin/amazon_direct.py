'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5479
'''

import csv
import os
from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider 

HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonDirect(BaseAmazonSpider):
    name = 'maplin-amazon_direct'
    type = 'search'
    amazon_direct = True
    domain = "amazon.co.uk"
    try_suggested = False
    
    file_path = HERE + '/products.csv'
    
    def get_search_query_generator(self):
        with open(self.file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Manufacturer part code']:
                    yield(row['Manufacturer part code'],
                          {'name': row['Description'], 'price': '', 'sku': row['Manufacturer part code']})
                    
    def match(self, meta, search_item, found_item):
        found_item['sku'] = search_item['sku']
        return True                    
    