# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4748

The spider uses amazon base spider, however it overwrites `parse_product_list` method
to satisfy requirement - filter by brand.

The spider is based on Amazon Direct spider of the same account, only difference is that
it collects all non-amazon seller prices

"""
import os

from amazondirect import GuitarGuitarAmazonCoUkBaseSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class GuitarGuitarAmazonCoUk3rdPartyTest(GuitarGuitarAmazonCoUkBaseSpider):
    name = 'guitarguitar_amazon.co.uk_3rd_party_test'
    domain = 'amazon.co.uk'

    type = 'category'
    all_sellers = True
    exclude_sellers = ['Amazon']

    def __init__(self, *args, **kwargs):
        super(GuitarGuitarAmazonCoUk3rdPartyTest, self).__init__(*args, **kwargs)

        self.brands = ['Yamaha']
