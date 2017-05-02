# -*- coding: utf-8 -*-
from base_spiders.amazonspider2.amazonspider import BaseAmazonSpider


class SSDBTestSpider3(BaseAmazonSpider):
    name = 'ssdb_test_spider_3'
    domain = 'amazon.ca'
    type = 'asins'
    amazon_direct = True
    parse_options = True

    def get_asins_generator(self):
        asins = [
            'B0000A0AGP',
            'B000051ZO9',
            'B00NA00MWS',
            'B00LEA5EHO',
            'B005TJMC0S',
            'B018R0C6RY',
            'B006RT5SUK',
        ]

        for asin in asins:
            yield asin, None
