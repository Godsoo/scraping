import os
from product_spiders.base_spiders import BaseeBaySpider
from product_spiders.utils import extract_price


class MusicroomEbaySpider(BaseeBaySpider):

    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'musicroom-ebay.co.uk'

    def __init__(self, *args, **kwargs):
        super(MusicroomEbaySpider, self).__init__()
        self._exclude_sellers = []
        self._search_fields = ['isbn', 'ean', 'upc']
        self._all_vendors = True
        self._meta_fields = [('sku', 'UniqueProductCode'),
                             ('identifier', 'UniqueProductCode'),
                             ('name', 'ProductName'),
                             ('brand', 'Brand'),
                             ('price', 'PriceGBP'),
                             ('category', 'Category')]
        self._try_replacing = []
        self._match_fields = ['sku']
        self._format_fields = [('PriceGBP', extract_price)]
        self._search_criteria = self.ANY_ANY_ORDER
        self._check_valid_currency = self.__check_valid_currency
        self._extract_stock_amount = True

    def start_requests(self):
        items = []

        fields = ['UniqueProductCode', 'isbn', 'ean', 'upc', 'ProductName', 'PriceGBP', 'ProductPageURL', 'Brand',
                  'Category', 'ImageURL', 'Stock', 'ShippingCost']
        filename = 'IntelligentEye.txt'
        with open(self.HERE + '/' + filename) as f:
            content = f.readlines()
            rows = []
            for line in content:
                line = line.decode('cp865', 'ignore')
                values = line.split('\t')
                rows.append(dict(zip(fields, values)))
            # The longer sentences first
            items = sorted(rows,
                           key=lambda _row: len(' '.join(_row[field] for field in self._search_fields)),
                           reverse=True)
        number = 0
        for row in items:
            number += 1
            for field, func_format in self._format_fields:
                row[field] = func_format(row[field])
            meta = dict(dict((m_k, row[m_f]) for m_k, m_f in self._meta_fields))
            search = ' '.join(row[field].strip().strip(chr(0)) for field in self._search_fields)
            meta.update({'search': search})
            # Get URL
            search = self._clean_search(search)  # Clean search
            url = self._get_url_search(search)
            self.log('Item %s | SKU: %s | Search by: %s' % (number,
                                                            meta.get('sku', None),
                                                            search))
            yield self._search(url, meta)

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