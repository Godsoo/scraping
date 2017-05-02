# -*- coding: utf-8 -*-
import re
import os

from decimal import Decimal

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders.amazonspider2.amazonspider import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonScraper, AmazonFilter

from product_spiders.fuzzywuzzy.fuzz import ratio, partial_ratio
from product_spiders.fuzzywuzzy import utils

minifigures_words = [
    'mini figures',
    'mini figure',
    'minifigures',
    'minifigure',
    'from set',
    'from sets',
    'minifig',
    'loose',
    'nobox',
    'from set',
    'from sets'
]

def _filter_name(name):
    """
    Filter auxiliary words from product name, like 'new offers for...'
    :param name: product name
    :type name: str
    :return: filtered name
    :rtype: str

    >>> _filter_name('New Offers for Lego Ninjago')
    'Lego Ninjago'
    >>> _filter_name('Lego Ninjago Jouet de Premier')
    'Lego Ninjago'
    """
    words_to_filter_out = ['new offers for']

    res = name[:]
    for word in words_to_filter_out:
        m = re.search(word, name, re.I)
        if m:
            res = res.replace(m.group(0), '')
            res = res.strip()
    return res

def filter_category(name, category):
    category = category.lower()
    m = re.search(category, name, re.I)
    res = name[:]
    if m:
        res = name.replace(m.group(0), '')
        res = res.strip()
    return res

def name_fuzzy_score(product1, product2):
    product1 = _filter_name(product1)
    product2 = _filter_name(product2)

    s1 = utils.full_process(product1)
    s2 = utils.full_process(product2)
    return ratio(s1, s2)

def name_fuzzy_partial_score(product1, product2):
    product1 = _filter_name(product1)
    product2 = _filter_name(product2)

    s1 = utils.full_process(product1)
    s2 = utils.full_process(product2)
    return partial_ratio(s1, s2)

def name_fuzzy_match(product1, product2):
    product1 = _filter_name(product1)
    product2 = _filter_name(product2)

    if name_fuzzy_score(product1, product2) > 50:
        return True
    return False

def check_max_price(search_price, price, price_diff=0.5):
    """
    Checks price variation

    >>> check_max_price(12, 60)
    False
    >>> check_max_price(60, 12)
    False
    >>> check_max_price(30, 60)
    True
    >>> check_max_price(60, 30)
    False
    >>> check_max_price(12, 60, 0.8)
    True
    >>> check_max_price(60, 12, 0.8)
    False
    >>> check_max_price(99, 186, 0.6)
    True
    >>> check_max_price(99, 186, 0.5)
    True
    >>> check_max_price(12, 60, 0.7)
    False
    >>> check_max_price(149.99, 499, 1)
    True
    """
    search_price = Decimal(search_price)
    price = Decimal(price)
    diff = abs(price - search_price)
    matches = diff / price <= price_diff
    return matches

def check_price_valid(search_price, price, min_ratio=0.5, max_ratio=3):
    """
    Checks price variation for lego.
    Ensures that price is between min_ratio * search_price and max_ratio * search_price

    >>> check_price_valid(12, 60)
    False
    >>> check_price_valid(60, 12)
    False
    >>> check_price_valid(30, 60)
    True
    >>> check_price_valid(60, 30)
    True
    >>> check_price_valid(99, 186)
    True
    >>> check_price_valid(99, 186)
    True
    >>> check_price_valid(12, 60)
    False
    >>> check_price_valid(149.99, 499, max_ratio=5)
    True
    >>> check_price_valid(319.99, 39.95)
    False
    >>> check_price_valid(Decimal('319.99'), Decimal('39.95'))
    False
    """
    if search_price is None:
        return False
    if price is None:
        return True
    if isinstance(search_price, float):
        search_price = Decimal(str(search_price))
    else:
        search_price = Decimal(search_price)

    if isinstance(price, float):
        price = Decimal(str(price))
    else:
        price = Decimal(price)

    if isinstance(min_ratio, float):
        min_ratio = Decimal(str(min_ratio))
    else:
        min_ratio = Decimal(min_ratio)

    if isinstance(max_ratio, float):
        max_ratio = Decimal(str(max_ratio))
    else:
        max_ratio = Decimal(max_ratio)

    if min_ratio * search_price <= price <= max_ratio * search_price:
        return True
    return False

def sku_match(search_item, new_item):
    _re_sku = re.compile(r'(\d{3,})')
    sku = _re_sku.findall(new_item['name'].replace(' ', ''))
    sku.extend(_re_sku.findall(new_item['name']))
    sku = set(sku)

    search_price = search_item.get('price')

    if sku:
        if len(sku) <= 1:
            match_sku = search_item['sku'] in sku
            return match_sku
        elif search_price:
            match_sku = search_item['sku'] in sku
            if isinstance(new_item['price'], tuple):
                valid_price = any([check_price_valid(search_price, x) for x in new_item['price']])
            else:
                valid_price = check_price_valid(search_price, new_item['price'])
            if not valid_price:
                return False
            return match_sku
        else:
            return False
    else:
        return False

def brand_match(new_item):
    brand = new_item.get('brand', '')
    if brand is None:
        return False
    brand = brand.upper()
    brand_matches = brand == 'LEGO' or brand.startswith('LEGO ') \
        or 'LEGO' in new_item['name'].upper()
    return brand_matches


_re_sku = re.compile(r'(\d{3,})')


def _check_max_price(search_price, price):
    """ Checks price variation
    >>> _check_max_price('74.99', '120')
    True
    """
    price_mult = 1
    search_price = Decimal(search_price)
    diff = Decimal(search_price) * Decimal(price_mult)
    if isinstance(price, tuple):
        res = any([Decimal(x) <= search_price + diff for x in price])
    else:
        res = Decimal(price) <= search_price + diff
    return res


class LegoAmazonScraper(AmazonScraper):

    def _process_search_results(self, response, results, amazon_direct=False):
        products = super(LegoAmazonScraper, self)._process_search_results(response, results, amazon_direct)
        for product in products:
            result = product['result']
            brand = result.select(u'.//h2/strong[1]/text()').extract()
            if not brand:
                brand = result.select(u'.//h3/span[contains(text(),"by")]/text()').extract()
            if not brand:
                brand = result.select(u'.//h3/span[contains(text(),"von")]/text()').extract()
            if not brand:
                brand = result.select(u'.//div[span[contains(text(),"by")]]/span[2]/text()').extract()

            if brand:
                product['brand'] = AmazonFilter.filter_brand(brand[0])

        return products


class BaseLegoAmazonSpider(BaseAmazonSpider):
    do_retry = True

    # download_delay = 1.0
    # randomize_download_delay = True

    skus_found = []
    errors = []
    exclude_products = []

    lego_amazon_domain = 'www.amazon.com'

    try_suggested = False

    scraper_class = LegoAmazonScraper

    def __init__(self, *args, **kwargs):
        self.domain = self.lego_amazon_domain
        super(BaseLegoAmazonSpider, self).__init__(*args, **kwargs)

    def match_min_price(self, search_item, new_item, price_diff=0.5):
        ''' Checks price variation '''
        search_price = search_item.get('price', None)
        if not search_price:
            return True
        search_price = Decimal(search_price)
        diff = Decimal(search_price) * Decimal(price_diff)
        if isinstance(new_item['price'], tuple):
            matches = any([search_price - diff <= Decimal(x) for x in new_item['price']])
        else:
            matches = search_price - diff <= Decimal(new_item['price'])
        if not matches:
            self.log('Item price is too different from %s, reject %s' % (search_price, new_item))
        return matches

    def match_lego_name(self, search_item, new_item):
        sku = _re_sku.findall(new_item['name'].replace(' ', ''))
        sku.extend(_re_sku.findall(new_item['name']))
        sku = set(sku)

        search_price = search_item.get('price')

        if sku:
            if not len(sku) > 1:
                match_sku = search_item['sku'] in sku
                self.log('SKU %s in %s ? %s' % (search_item['sku'], sku, match_sku))
                return match_sku
            elif search_price:
                match_sku = search_item['sku'] in sku
                self.log('SKU %s in %s ? %s' % (search_item['sku'], sku, match_sku))
                valid_price = _check_max_price(search_price, new_item['price'])
                if not valid_price:
                    self.log('Reject lot of products => %s' % new_item['url'])
                    return False
                return match_sku
            else:
                self.log('Reject lot of products => %s' % new_item['url'])
                return False

        return self.match_name(search_item, new_item, match_threshold=70)

    def match(self, meta, search_item, new_item):
        return (self.match_min_price(search_item, new_item)
                and self.match_lego_name(search_item, new_item)
                and not self._excluded_product(new_item['name'])
                and self._valid_terms(new_item['name']))

    def _excluded_product(self, product_name):
        for product in self.exclude_products:
            if product.upper() in product_name.upper():
                return True
        return False

    def _valid_terms(self, item_name):
        '''
        [([<list terms to exclude>], [<list exceptions>]),
         ([...], [...]),
         ([...], [...])]
        '''
        item_name = item_name.lower()
        exclude_ = [(['NO MINIFIG'], []),
                    (['FROM SET'], []),
                    (['MINIFIG', 'MINIFG'], ['MINIFIGURES', 'INCLUDE'])]
        for values, exceptions in exclude_:
            for w in values:
                if w.lower() in item_name:
                    # searching for exceptions of exclude
                    for e in exceptions:
                        if e.lower() in item_name:
                            break
                    else:
                        # no exception found - item name is not valid because contains word, which should be excluded
                        return False
        return True

