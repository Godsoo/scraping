# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4721

The spider uses amazon base spider, search type, searching for "Vonshef",
extracting all and only 3rd party prices (not amazon).
Collect reviews only from verified purchase

"""
import os

from amazon_savisto_3rd_party import BaseAndrewJamesAmazonCoUkSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class AndrewJamesAmazonCoUkVonshef3rdParth(BaseAndrewJamesAmazonCoUkSpider):
    name = 'andrewjames_amazon.co.uk_vonshef_3rdparty'
    brands = [
        'Vonshef'
    ]
