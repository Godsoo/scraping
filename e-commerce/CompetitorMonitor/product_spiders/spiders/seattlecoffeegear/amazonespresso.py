import os
import csv

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class AmazonComSpider(BaseAmazonSpider):
    name = 'amazon.com_espresso'

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:24.0) Gecko/20100101 Firefox/24.0'

    exclude_sellers = ['ATVPDKIKX0DER', '3dRose']

    domain = 'amazon.com'
    type = 'category'
    only_buybox = True

    collect_products_with_no_dealer = True
    dealer_is_mandatory = False
    collect_products_from_list = True

    semicolon_in_identifier = False

    _max_pages = 400

    do_retry = True

    def __init__(self, *args, **kwargs):
        super(AmazonComSpider, self).__init__(*args, **kwargs)

        self.amazon_espresso_brands = {}

        fname = os.path.join(HERE, 'amazonespresso.csv')
        if os.path.exists(fname):
            with open(fname) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.amazon_espresso_brands[row['identifier']] = row['brand'].decode('utf8')

    def get_category_url_generator(self):
        search_urls = [
            "http://www.amazon.com/s/ref=nb_sb_noss?keywords=espresso&node=%(node)s",
            "http://www.amazon.com/s/ref=nb_sb_noss?keywords=kettle&node=%(node)s",
        ]

        category_ids = [
            ('2251595011', 'Grocery & Gourmet Food'),
            ('2251593011', 'Grocery & Gourmet Food'),
            ('2251592011', 'Grocery & Gourmet Food'),
            ('915194', 'Grocery & Gourmet Food'),
        ]

        for cat_id, cat_name in category_ids:
            for search_url in search_urls:
                yield (search_url % {'node': cat_id}, cat_name)

    def match(self, meta, search_item, found_item):
        """
        >>> a = AmazonComSpider()
        >>> a.match({}, {}, {'name': 'cgb_171713_1 Florene Vintage II - image of vintage typography which says wine list - Coffee Gift Baskets - Coffee Gift Basket'})
        False
        """
        if 'cgb_' in found_item['name'] and 'Coffee Gift Basket'.lower() in found_item['name'].lower():
            return False

        return super(AmazonComSpider, self).match(meta, search_item, found_item)

    def get_subrequests_for_search_results(self, response, search_results_data, max_pages=0):
        current_errors = self.errors[:]
        res = super(AmazonComSpider, self).get_subrequests_for_search_results(response, search_results_data, max_pages)
        self.errors = current_errors
        return res
