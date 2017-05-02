import os
import csv
import cStringIO

from decimal import Decimal

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class AnglingDirectAmazonSpider(BaseAmazonSpider):
    name = 'anglingdirect-amazon.com'

    use_amazon_identifier = False

    domain = 'amazon.co.uk'

    lowest_product_and_seller = True
    lowest_seller_collect_dealer_identifier = False
    collect_products_with_no_dealer = True

    cache_filename = os.path.join(HERE, 'angling_amazon_data.csv')

    do_retry = True

    def get_search_query_generator(self):
        self.errors.append("Spider works incorrectly: "
                           "it should use main spider's last crawl results, but uses local file")
        # FIXME: should use main spider's crawl results from `data` folder. See example: `axemusic/amazon_spider.py`

    def match(self, meta, search_item, found_item):
        self.log('%s: %s' % (found_item['identifier'], found_item['name']))
        self.log("[[TESTING]] Search item: %s" % str(search_item))
        self.log("[[TESTING]] Found item: %s" % str(found_item))
        return self.match_name(search_item, found_item) \
            and self.match_price(search_item, found_item)

    def construct_product(self, item, meta=None, use_seller_id_in_identifier=None):
        item = super(AnglingDirectAmazonSpider, self).construct_product(item, meta, use_seller_id_in_identifier)
        if 'shipping_cost' in item and item['shipping_cost'] and item['price']:
            shipping = Decimal(item['shipping_cost'])
            price = Decimal(item['price'])
            item['price'] = price + shipping
            item['shipping_cost'] = ''

        return item
