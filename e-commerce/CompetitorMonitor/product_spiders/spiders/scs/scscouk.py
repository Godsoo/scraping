# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class ScSSpider(SecondaryBaseSpider):
    name = "scs-scs.co.uk"
    allowed_domains = ('scs.co.uk', )
    start_urls = ['http://www.scs.co.uk/']

    csv_file = 'harveys/scs.co.uk_products.csv'
