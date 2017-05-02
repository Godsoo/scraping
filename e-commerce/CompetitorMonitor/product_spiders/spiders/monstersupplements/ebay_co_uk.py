import os

from decimal import Decimal
from product_spiders.base_spiders import BaseeBaySpider


class MonstersupplementsEbaySpider(BaseeBaySpider):

    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'monstersupplements-ebay.co.uk'

    def __init__(self, *args, **kwargs):
        super(MonstersupplementsEbaySpider, self).__init__()
        self._csv_file = os.path.join(self.HERE, 'monstersupplements.csv')
        self._exclude_sellers = []
        self._search_fields = ['name']
        self._all_vendors = False
        self._meta_fields = [('sku', 'sku'),
                             ('identifier', 'identifier'),
                             ('name', 'name'),
                             ('brand', 'brand'),
                             ('price', 'price')]
        self._try_replacing = [('FREE', ''),
                               ('lb', ''),
                               ('lbs', ''),
                               ('grams', ''),
                               ('lb.', ''),
                               ('100%', ''),
                               ('+', ''),
                               ('unflavoured', ''),
                               ('new', ''),
                               ('new formula', ''),
                               ('liquid', ''),
                               ('*', 'x'),
                               ('*', '')]
        self._match_fields = ['sku', 'identifier']
        self._search_criteria = self.DEFAULT_CRITERIA

    def _clean_search(self, search):
        redundant = (('&', ''), ('/', ''), ('(', ''), (')', ''), ('-', ' '),
                     (':', ' '), ('[', ''), (']', ''), ('{', ''), ('}', ''))
        for replacement in redundant:
            search = search.replace(replacement[0], replacement[1])
        return search



