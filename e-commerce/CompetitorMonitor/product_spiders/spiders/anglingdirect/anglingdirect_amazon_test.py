import os
import csv
import cStringIO

from product_spiders.base_spiders import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class AnglingDirectAmazonSpider(BaseAmazonSpider):
    name = 'anglingdirect-amazon.com_test'

    collect_products_with_no_dealer = True

    max_pages = 2

    def __init__(self, *args, **kwargs):
        super(AnglingDirectAmazonSpider, self).__init__('www.amazon.co.uk', *args, **kwargs)

    def start_requests(self):
        self.errors.append("Spider works incorrectly: "
                           "it should use main spider's last crawl results, but uses local file")
        # FIXME: should use main spider's crawl results from `data` folder. See example: `axemusic/amazon_spider.py`

    def match(self, search_item, new_item):
        self.log('%s: %s' % (new_item['identifier'], new_item['name']))
        return self.match_name(search_item, new_item) \
            and self.match_price(search_item, new_item)

