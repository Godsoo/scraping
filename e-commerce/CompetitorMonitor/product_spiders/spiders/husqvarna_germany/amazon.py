# -*- coding: utf-8 -*-
__author__ = 'juraseg'
import os

from urlparse import urljoin

from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class HusqvarnaGermanyAmazonSpider(BaseAmazonSpider):
    name = 'husqvarna-germany-amazon'
    domain = 'amazon.de'

    type = 'search'
    search_category = 'outdoor'  # 'Garten' on site
    all_sellers = True

    _use_amazon_identifier = True

    collect_products_from_list = False

    do_retry = True

    model_as_sku = True

    max_pages = None

    def get_search_query_generator(self):
        brands = [
            'AL-KO',
            'Ambrogio',
            'Black & Decker',
            'Bosch',
            'Castel Garden',
            'Core',
            'CubCadet',
            'Dolmar',
            'Echo',
            'Gardena',
            'Hitachi',
            'Honda',
            'Husqvarna',
            'John Deere',
            'Makita',
            'Oregon',
            'Pellenc',
            'Robomow',
            'Ryobi',
            'Shindaiwa',
            'Stiga',
            'Stihl',
            'Viking',
            'Wolf Garten',
            'Worx',
        ]

        for brand in brands:
            yield (brand, {})

    def parse_product_list(self, response):
        # if "Marke" is found - redirect to it
        hxs = HtmlXPathSelector(response)

        brand_filter_container = hxs.select("//ul[@id='ref_669059031']")
        if not brand_filter_container or not response.meta.get('filter_for_brand', True):
            for x in super(HusqvarnaGermanyAmazonSpider, self).parse_product_list(response):
                yield x
            return

        else:
            search_brand_name = response.meta['search_string']
            for el in brand_filter_container.select("li/a"):
                brand_name = el.select("span/text()").extract()[0]
                if brand_name.lower() != search_brand_name.lower():
                    continue

                url = el.select("@href").extract()[0]
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
