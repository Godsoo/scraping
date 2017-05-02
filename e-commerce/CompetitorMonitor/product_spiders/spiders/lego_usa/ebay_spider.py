import os
import re
import csv
import cStringIO

from decimal import Decimal

from product_spiders.base_spiders import BaseeBaySpider

from product_spiders.base_spiders.matcher import Matcher

HERE = os.path.abspath(os.path.dirname(__file__))


class LegoUsaEbaySpider(BaseeBaySpider):

    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'legousa-ebay.com'

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'ebay_map_deviation.csv')
    map_screenshot_method = 'scrapy_response'
    map_screenshot_html_files = {}

    def __init__(self, *args, **kwargs):
        super(LegoUsaEbaySpider, self).__init__()
        self._csv_file = os.path.join(self.HERE, 'lego.csv')
        self._converted_price = True
        self._ebay_url = 'http://www.ebay.com'
        self._search_fields = [3, 2]
        self._all_vendors = True
        self._look_related = False
        self._meta_fields = [('sku', 2),
                             ('name', 3),
                             ('price', 4),
                             ('category', 1)]
        self._match_fields = ('sku', 'identifier')
        self._check_valid_item = self._valid_item_

        self._re_sku = re.compile(r'(\d{3,})')

        self._check_diff_ratio = True
        # self._ratio_accuracy = 60

        self.matcher = Matcher(self.log)

    def match_text(self, text, item_field, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(text, item_field, important_words)
        self.log('Searching for %s in %s: %s' % (text, item_field, r))
        return r >= match_threshold

    def start_requests(self):
        with open(self._csv_file) as f:
            reader = csv.reader(cStringIO.StringIO(f.read()))

            number = 0
            for row in reader:
                number += 1
                meta = dict(dict((m_k, row[m_f]) for m_k, m_f in self._meta_fields))
                search = ' '.join(row[field].strip() for field in self._search_fields)
                if not 'lego' in search.lower():
                    search = 'LEGO ' + search
                meta.update({'search': search})
                # Get URL
                search = self._clean_search(search)  # Clean search
                url = self._get_url_search(search)
                self.log('Item %s | SKU: %s | Search by: %s' % (number,
                                                                meta.get('sku', None),
                                                                search))
                yield self._search(url, meta)

                search = 'LEGO ' + row[2]
                meta.update({'search': search})
                # Get URL
                search = self._clean_search(search)  # Clean search
                url = self._get_url_search(search)
                self.log('Item %s | SKU: %s | Search by: %s' % (number,
                                                                meta.get('sku', None),
                                                                search))
                yield self._search(url, meta)

    def load_item(self, *args, **kwargs):
        product_loader = super(LegoUsaEbaySpider, self).load_item(*args, **kwargs)
        product_loader.replace_value('brand', 'LEGO')

        identifier = product_loader.get_output_value('identifier')
        response = args[-1]

        html_path = os.path.join('/tmp', 'ebay_%s.html' % identifier)
        with open(html_path, 'w') as f_html:
            f_html.write(response.body)
        self.map_screenshot_html_files[identifier] = html_path

        return product_loader

    def _valid_item_(self, item_loader, response):
        item_name = item_loader.get_output_value('name').lower()

        if not self._check_exclude_terms(item_name):
            return False

        name = item_loader.get_output_value('name')
        search_sku = item_loader.get_output_value('sku')
        sku = self._re_sku.findall(name.replace(' ', ''))
        sku.extend(self._re_sku.findall(name))
        category = item_loader.get_output_value('category')

        if not self._check_name_valid(name):
            return False

        if not self._check_category_valid(category):
            return False

        sku = set(sku)

        search_name = response.meta['item_meta']['name'].decode('utf-8')
        if not self.match_text(search_name, name, match_threshold=70):
            return False

        if sku:
            search_price = response.meta['item_meta'].get('price')
            price = item_loader.get_output_value('price')
            if not len(sku) > 1 or self._check_max_price(search_price, price):
                match_sku = search_sku in sku
                self.log('SKU %s in %s ? %s' % (search_sku, sku, match_sku))
                return match_sku
            else:
                self.log('Reject lot of products => %s' % item_loader.get_output_value('url'))
                return False

        return True

    def _check_name_valid(self, name):
        """
        >>> spider = LegoUsaEbaySpider()
        >>> spider._check_name_valid("Lego 123")
        True
        >>> spider._check_name_valid("Lego 123 figure")
        False
        """
        if (self.match_text('mini figures from', name)
                or self.match_text('mini figures only', name)
                or self.match_text('mini figures', name)
                or self.match_text('mini figure', name)
                or self.match_text('minifigures', name)
                or self.match_text('minifigure', name)
                or self.match_text('figure', name)
                or self.match_text('loose', name)
                or self.match_text('no box', name)
                or self.match_text('nobox', name)):
            return False
        return True

    def _check_category_valid(self, category):
        """
        >>> spider = LegoUsaEbaySpider()
        >>> spider._check_category_valid('asd')
        True
        >>> spider._check_category_valid("figures")
        False
        >>> spider._check_category_valid("figure")
        False
        """
        if category and (
                    self.match_text('figure', category)
        ):
            return False
        return True

    def _check_valid_price(self, search_price, price):
        ''' Checks price variation '''
        price_diff = 0.5
        search_price = Decimal(search_price)
        diff = Decimal(search_price) * Decimal(price_diff)
        return search_price - diff <= Decimal(price)

    def _check_max_price(self, search_price, price):
        ''' Checks price variation '''
        price_diff = 0.5
        search_price = Decimal(search_price)
        diff = Decimal(search_price) * Decimal(price_diff)
        return Decimal(price) <= search_price + diff

    def _check_exclude_terms(self, item_name):
        '''
        [([<list terms to exclude>], [<list exceptions>]),
         ([...], [...]),
         ([...], [...])]
        '''
        exclude_ = [(['NO MINIFIG'], []),
                    (['MINIFIG', 'MINIFG'], ['MINIFIGURES'])]
        for values, exceptions in exclude_:
            for w in values:
                if w.lower() in item_name:
                    itsvalid = False
                    for e in exceptions:
                        if e.lower() in item_name:
                            itsvalid = True
                            break
                    if not itsvalid:
                        return False
        return True
