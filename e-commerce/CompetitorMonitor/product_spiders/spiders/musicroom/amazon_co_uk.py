import os
from scrapy.http import Request

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider, AmazonUrlCreator

HERE = os.path.abspath(os.path.dirname(__file__))


class MusicroomAmazonSpider(BaseAmazonSpider):
    name = 'musicroom-amazon.co.uk'
    domain = 'www.amazon.co.uk'
    all_sellers = True
    _use_amazon_identifier = True
    exclude_sellers = ['Amazon']
    max_pages = 1
    #download_delay = 1.0
    #randomize_download_delay = True
    do_retry = 1
    retry_sleep = 10
    collect_new_products = True
    collect_used_products = False

    try_suggested = False

    def __init__(self, *args, **kwargs):
        super(MusicroomAmazonSpider, self).__init__(*args, **kwargs)
        self.try_suggested = False
        self.current_searches = []

    def get_search_query_generator(self):
        """
        This spider differs a little from what base spider provides. For each item in list it needs firstly to search
        by ISBN, EAN, UPC and by name consequently, and only search using next method if previous failed. So if
        product is found by ISBN than just skip other search methods.

        To make it work this function outputs all possible searches. It also outputs `match_method` for each
        search strings. Match method can be of two values 'all' and 'best_match'. All means to just collect all
        found products, 'best_match' makes it collect only best matched by name product
        """
        fields = ['UniqueProductCode', 'isbn', 'ean', 'upc', 'ProductName', 'PriceGBP', 'ProductPageURL', 'Brand',
                  'Category', 'ImageURL', 'Stock', 'ShippingCost']
        filename = 'IntelligentEye.txt'
        with open(HERE + '/' + filename) as f:
            content = f.readlines()
            for i, line in enumerate(content):
                line = line.decode('cp865', 'ignore')
                values = line.split('\t')
                data = dict(zip(fields, values))
                search_strings = []

                ss = data['isbn'].strip().strip(chr(0))
                if ss:
                    search_strings.append((ss, "code"))
                ss = data['ean'].strip().strip(chr(0))
                if ss:
                    search_strings.append((ss, "code"))
                ss = data['upc'].strip().strip(chr(0))
                if ss:
                    search_strings.append((ss, "code"))
                ss = data['ProductName'].strip().strip(chr(0))
                if ss:
                    search_strings.append((ss, "string"))

                if search_strings:
                    item = {
                        'sku': data['UniqueProductCode'],
                        'name': data['ProductName'],
                        'category': data['Category'],
                        'price': data['PriceGBP'],
                    }
                    yield (search_strings, item)

    def get_next_search_request(self, callback=None):
        """
        This differs from how it works in base spider due to spider requirements. Check `get_search_query_generator`
        documentation for brief introduction

        To make it work how intended this spider uses additional attribute - `current_searches`. It stores all
        possible searches. The function takes search string (and relevant match_method) one by one and launches
        search on them. If `current_searches` is empty it takes next search item from generator
        """
        if not self.current_searches or self.processed_items:
            if not self.search_generator:
                return None
            try:
                search_strings, search_item = next(self.search_generator)
            except StopIteration:
                return None

            self.current_search_item = search_item
            self.collected_items = []
            self.processed_items = False
            self.current_searches = search_strings

        search_string, match_method = self.current_searches.pop(0)

        self.log('Searching for [%s]' % search_string)

        self.current_search = search_string

        requests = []
        url = AmazonUrlCreator.build_search_url(self.domain, search_string, self.amazon_direct)

        if callback is None:
            callback = self.parse_product_list

        requests.append(Request(
            url,
            meta={'search_string': search_string, 'match_method': match_method, 'search_item': self.current_search_item},
            dont_filter=True, callback=callback
        ))

        return requests

    def match(self, meta, search_item, new_item):
        if meta.get('match_method', '') == "code":
            return True
        else:
            # match last search item against the name (as last search variation is by Name)
            return self.match_name(meta['search_item'], new_item)
