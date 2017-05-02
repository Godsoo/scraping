# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4614

The spider uses amazon base spider, however it overwrites `parse_product_list` method
to satisfy requirement - filter brand to 'Camelbak'

"""
import os

from urlparse import urljoin

from scrapy.utils.response import get_base_url
from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class CamelbakUKAmazonCoUKMarketplace(BaseAmazonSpider):
    name = 'camelbakuk_amazon.co.uk_marketplace'
    domain = 'amazon.co.uk'

    type = 'search'
    all_sellers = True

    _use_amazon_identifier = True

    parse_options = True

    do_retry = True
    model_as_sku = True

    max_pages = None

    def get_search_query_generator(self):
        brands = [
            'Camelbak'
        ]

        for brand in brands:
            yield (brand, {})

    def parse_product_list(self, response):
        if not response.meta.get('filter_for_brand', True):
            for x in super(CamelbakUKAmazonCoUKMarketplace, self).parse_product_list(response):
                yield x
            return

        else:
            brand_filter_container = response.xpath("//ul[@id='ref_1632651031']")
            search_brand_name = response.meta['search_string']
            for el in brand_filter_container.xpath("li/a"):
                brand_name = el.xpath("span/text()").extract()[0]
                if brand_name.lower() != search_brand_name.lower():
                    continue

                url = el.xpath("@href").extract()[0]
                url = urljoin(get_base_url(response), url)
                new_meta = response.meta.copy()
                new_meta.update({
                    'filter_for_brand': False
                })
                yield Request(
                    url,
                    meta=new_meta,
                    dont_filter=True,
                    callback=self.parse_product_list
                )

    def match(self, meta, search_item, found_item):
        return True
