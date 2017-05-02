import csv
import os
from product_spiders.base_spiders import BaseeBaySpider

HERE = os.path.abspath(os.path.dirname(__file__))


class TheBookPeopleEbaySpider(BaseeBaySpider):
    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'thebookpeople-ebay.co.uk'

    def __init__(self, *args, **kwargs):
        super(TheBookPeopleEbaySpider, self).__init__()
        self._csv_file = os.path.join(HERE, 'thebookpeople.co.uk_products.csv')
        self._exclude_sellers = []
        self._search_fields = ['sku']
        self._all_vendors = True
        self._meta_fields = [
            # ('sku', 'ISBN')
            ('sku', 'sku')
        ]
        self._try_replacing = []
        self._match_fields = ['sku']
        self._search_criteria = self.ANY_ANY_ORDER
        self._check_valid_currency = self.__check_valid_currency
        self._extract_stock_amount = True

    def _clean_search(self, search):
        redundant = (('&', ''), ('/', ''), ('(', ''), (')', ''), ('-', ' '),
                     (':', ' '), ('[', ''), (']', ''), ('{', ''), ('}', ''))
        for replacement in redundant:
            search = search.replace(replacement[0], replacement[1])
        return search

    def _check_valid_price(self, site_price, price):
        return True

    def __check_valid_currency(self, currency):
        return currency == u'\xa3'
