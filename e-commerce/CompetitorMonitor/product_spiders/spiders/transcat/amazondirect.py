# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4826

The spider uses amazon base spider, it searches site using data from main spiders results: Brand + MPN
Collects reviews only for matched products
"""
import json
import csv
import os.path

from scrapy import log
from product_spiders.base_spiders.amazonspider2.amazonspider_concurrent import BaseAmazonConcurrentSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper


from product_spiders.config import DATA_DIR

from transcatitems import TranscatMeta

from product_spiders.utils import extract_price


class AmazonScraperTranscat(AmazonScraper):

    def scrape_product_details_page(self, response, only_color=False,
                                    collect_new_products=True,
                                    collect_used_product=False):
        product = super(AmazonScraperTranscat, self).scrape_product_details_page(response, only_color,
                                                                                 collect_new_products,
                                                                                 collect_used_product)

        if not product:
            return product

        if not product['price']:
            price = response.xpath('//span[@id="priceblock_ourprice"]//text()').re('\d+')
            if price:
                price = extract_price('.'.join(price))
                product['price'] = price

        strike = response.xpath('//span[@class="a-text-strike"]/text()').extract()

        product['strike'] = strike[0].strip() if strike else ''

        return product


class TranscatAmazonDirectSpider(BaseAmazonConcurrentSpider):
    name = 'transcat-amazon.com-direct'
    domain = 'amazon.com'
    type = 'search'
    amazon_direct = True

    try_suggested = False

    model_as_sku = True

    collect_reviews = True
    reviews_only_matched = True

    main_website_id = 1658

    scraper_class = AmazonScraperTranscat

    def get_search_query_generator(self):
        # we have to yield a dummy request because "start_requests" happen before "spider_opened" in
        # UpdateManagerExtension extension, where "main_website_last_crawl_id" attribute is set
        yield None, {}
        try:
            main_spider_last_crawl_results_filepath = os.path.join(
                DATA_DIR, '{}_products.csv'.format(self.main_website_last_crawl_id))
            main_spider_last_crawl_meta_filepath = os.path.join(
                DATA_DIR, 'meta/{}_meta.json-lines'.format(self.main_website_last_crawl_id))
        except AttributeError:
            msg = "Couldn't find latest crawl for main spider (id={})".format(self.main_website_id)
            self.errors.append(msg)
            self.log(msg, level=log.CRITICAL)
            self.close(self, msg)
            return

        # we can't use metadata results as they store metadata for all product, which were crawled by spider in all time
        meta = {}
        with open(main_spider_last_crawl_meta_filepath) as f:
            for line in f:
                data = json.loads(line)
                meta[data['identifier']] = data['metadata']['mpn']

        with open(main_spider_last_crawl_results_filepath) as f:
            for i, row in enumerate(csv.DictReader(f)):
                brand = row['brand']
                mpn = meta[row['identifier']]
                search_string = "{} {}".format(brand, mpn)
                self.log("[[Child spider]] Searching for: {} {}".format(i, search_string))
                yield search_string, {}

    def match(self, meta, search_item, found_item):
        return True

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        # Strike Through Price
        transcat_metadata = TranscatMeta()
        if item.get('strike'):
            transcat_metadata['strike'] = item.get('strike', '')

        product = super(TranscatAmazonDirectSpider, self).construct_product(item, meta, use_seller_id_in_identifier)

        product['metadata'] = transcat_metadata
        return product
