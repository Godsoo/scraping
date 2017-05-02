import os
import csv
import cStringIO

from scrapy import log

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.config import DATA_DIR

HERE = os.path.abspath(os.path.dirname(__file__))


class AxeMusicAmazonSpider(BaseAmazonSpider):
    name = 'axemusicfeed-amazon.com'
    domain = 'amazon.com'

    type = 'search'
    lowest_product_and_seller = True
    max_pages = 1
    collect_products_from_list = True

    main_website_id = 252

    def get_search_query_generator(self):
        yield None, {}
        try:
            main_spider_last_crawl_results_filepath = os.path.join(
                DATA_DIR, '{}_products.csv'.format(self.main_website_last_crawl_id))
        except AttributeError:
            msg = "Couldn't find latest crawl for main spider (id={})".format(self.main_website_id)
            self.errors.append(msg)
            self.log(msg, level=log.CRITICAL)
            self.close(self, msg)
            return
        with open(main_spider_last_crawl_results_filepath) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for i, row in enumerate(reader):
                yield row['name'], row

    def match(self, meta, search_item, found_item):
        return self.match_name(search_item, found_item) \
            and self.match_price(search_item, found_item)
