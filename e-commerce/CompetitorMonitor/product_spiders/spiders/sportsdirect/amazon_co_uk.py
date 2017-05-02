# -*- coding: utf-8 -*-
__author__ = 'juraseg'

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider


class SportsDirectAmazonSpider(BaseAmazonSpider):
    name = 'sportsdirect-amazon.co.uk'
    domain = 'amazon.co.uk'

    type = 'category'

    only_buybox = True

    parse_options = True
    options_only_color = True

    _use_amazon_identifier = True
    model_as_sku = True

    do_retry = True

    _max_pages = 200

    def get_category_url_generator(self):
        urls = [('http://www.amazon.co.uk/s/ref=nb_sb_noss?url=search-alias%3Dshoes&field-keywords=nike', '')]

        for url, category_name in urls:
            yield url, category_name
