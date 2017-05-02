import os
import csv

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.spiders.lego_cz.legoitems import LegoMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class LegoMetadataBaseSpider(BaseSpider):

    def __init__(self, *args, **kwargs):
        super(LegoMetadataBaseSpider, self).__init__(*args, **kwargs)
        self.functional_discount = {}
        with open(os.path.join(HERE, 'monitoring_customers.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.functional_discount[row['Web page']] = row['Functional discount']

    def load_item_with_metadata(self, item):
        metadata = LegoMeta()
        functional_discount = ''
        for site in self.functional_discount.keys():
            if site in item['url']:
                functional_discount = self.functional_discount[site]
                break

        metadata['functional_discount'] = functional_discount
        item['metadata'] = metadata
        return item
