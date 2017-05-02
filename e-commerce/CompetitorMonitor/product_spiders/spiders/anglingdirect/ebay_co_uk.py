import os

from scrapy import log

from product_spiders.base_spiders import BaseeBaySpider
from product_spiders.config import DATA_DIR


class AnglingDirectEbaySpider(BaseeBaySpider):

    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'anglingdirect-ebay.co.uk'

    main_website_id = 34727

    def __init__(self, *args, **kwargs):
        super(AnglingDirectEbaySpider, self).__init__()
        self._exclude_sellers = ['angling_warehouse']
        self._search_fields = ['name']
        self._all_vendors = False
        self._meta_fields = [('sku', 'sku'),
                             ('identifier', 'identifier'),
                             ('name', 'name'),
                             ('price', 'price')]
        self._match_fields = ('sku', 'identifier')
        self._converted_price = True

    def start_requests(self):
        # assign main site's last crawl results to self._csv_file
        try:
            self._csv_file = os.path.join(DATA_DIR, '{}_products.csv'.format(self.main_website_last_crawl_id))
        except AttributeError:
            msg = "Couldn't find latest crawl for main spider (id={})".format(self.main_website_id)
            self.errors.append(msg)
            self.log(msg, level=log.CRITICAL)
            self.close(self, msg)
            return
        else:
            self.log("Found main spider's previous crawl results")
        for r in super(AnglingDirectEbaySpider, self).start_requests():
            yield r
