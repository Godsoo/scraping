# -*- coding: utf-8 -*-
"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5015

The spider uses amazon base spider, however it overwrites `parse_product_list` method
to satisfy requirement - filter brand to 'Camelbak'

"""
import os

from urlparse import urljoin

from scrapy.utils.response import get_base_url
from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class CamelbakFRAmazonFrMarketplace(BaseAmazonSpider):
    name = 'camelbak_fr-amazon.fr_marketplace'
    domain = 'amazon.fr'

    type = 'category'
    all_sellers = True
    exclude_sellers = ['Amazon']

    _use_amazon_identifier = True

    parse_options = True

    do_retry = True

    model_as_sku = True

    max_pages = None


    def get_category_url_generator(self):
        urls = [('https://www.amazon.fr/s/ref=sr_nr_p_89_0?fst=as%3Aoff&rh=i%3Aaps%2Ck%3Acamelbak%2Cp_89%3ACamelBak&keywords=camelbak&ie=UTF8&qid=1468246446&rnid=1680780031', '')]

        for url, category_name in urls:
            yield url, category_name


    def match(self, meta, search_item, found_item):
        return True
