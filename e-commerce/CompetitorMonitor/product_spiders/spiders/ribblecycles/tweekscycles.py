# -*- coding: utf-8 -*-
from product_spiders.utils import extract_price

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class TweeksSpider(SecondaryBaseSpider):
    name = 'ribblecycles-tweekscycles.com'
    allowed_domains = ['tweekscycles.com']
    start_urls = ['http://www.tweekscycles.com/']

    csv_file = 'pedalpedal/tweekscycles_products.csv'

    def preprocess_product(self, item):
        if not item['price']:
            item['price'] = '0.00'
        elif extract_price(item['price']) < 9:
            item['shipping_cost'] = 1.99
        return item
