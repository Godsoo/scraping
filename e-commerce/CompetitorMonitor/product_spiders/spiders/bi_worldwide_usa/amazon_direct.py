# -*- coding: utf-8 -*-
import re
import json
import os.path
from decimal import Decimal

from scrapy.selector import HtmlXPathSelector

from product_spiders.base_spiders.amazonspider2.amazonspider_concurrent import BaseAmazonConcurrentSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper

from util import get_products_from_feed
from biwmeta import BIWMeta

MAX_SKU_LEN = 255

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonScraperBIW(AmazonScraper):

    def scrape_product_details_page(self, response, only_color=False,
                                    collect_new_products=True,
                                    collect_used_product=False):
        product = super(AmazonScraperBIW, self).scrape_product_details_page(response, only_color,
                                                                            collect_new_products,
                                                                            collect_used_product)

        if not product:
            return product

        hxs = HtmlXPathSelector(response)

        warranty = []
        warranty_elems = hxs.select('//div[@id="abbWrapper"]/fieldset//span[contains(@class,"a-checkbox-label")]')
        for elem in warranty_elems:
            warranty_period = elem.select('./span[@class="a-declarative"]/a/text()').extract()
            warranty_price = elem.select('./span[@class="a-color-price offer-price a-text-normal"]/text()').extract()
            if warranty_period and warranty_price:
                warranty.append({'period': warranty_period[0], 'price': warranty_price[0]})

        product['warranty'] = json.dumps(warranty)

        return product


class BIWAmazonDirectSpider(BaseAmazonConcurrentSpider):
    name = "biw_amazon_direct"
    domain = "amazon.com"

    extract_warranty = True

    type = 'search'
    amazon_direct = True

    try_suggested = False

    max_pages = 5
    model_as_sku = True

    file_start_with = 'BI USA File'
    prefix = 'amazon_direct_'
    file_extension = 'xlsx'
    root = HERE

    scraper_class = AmazonScraperBIW

    custom_settings = {
        'COOKIES_ENABLED': False,
    }

    def get_search_query_generator(self):
        for i, (search_str, product) in enumerate(get_products_from_feed(self.file_start_with, self.prefix, self.root, self.file_extension)):
            yield search_str, product

    def match(self, meta, search_item, found_item):
        return True

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        # Warranty
        biw_metadata = BIWMeta()
        if item.get('warranty'):
            warranty = json.loads(item.get('warranty', []))
            for elem in warranty:
                elem['price'] = Decimal(re.search('([\d\.]+)', elem.get('price', '0.00')).group(1))
            warranty = sorted(warranty, key=lambda x: x['price'], reverse=True)
            if len(warranty) > 0:
                warranty = str(warranty[0]['price'])
            else:
                warranty = ''
            biw_metadata['warranty'] = warranty

        product = super(BIWAmazonDirectSpider, self).construct_product(item, meta, use_seller_id_in_identifier)

        if self.extract_warranty:
            product['metadata'] = biw_metadata
        return product
