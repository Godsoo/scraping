"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5055
"""

import csv
import os
from decimal import Decimal

from scrapy.spiders import CSVFeedSpider
from product_spiders.items import Product

HERE = os.path.abspath(os.path.dirname(__file__))


class LampShopOnline(CSVFeedSpider):
    name = 'lampshoponline-lampshoponline'
    allowed_domains = []
    start_urls = ['file:' + os.path.join(HERE, 'products.csv')]
    
    def parse_row(self, response, row):
        product = Product()
        product['identifier'] = row['GTIN']
        product['sku'] = row['GTIN']
        product['name'] = row['Product Name']
        product['brand'] = row['Brand Name']
        product['category'] = row['Category']
        price = Decimal(row['Price Ex VAT']) * Decimal('1.2')
        product['price'] = price.quantize(Decimal('.01'))
        product['metadata'] = {'MPN': row['Manufacturer Part Number']}
        yield product
        