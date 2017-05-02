import re
import os
import shutil

from decimal import Decimal

from scrapy.selector import HtmlXPathSelector

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders import BaseAmazonSpider

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

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
            valid_price = check_price_valid(search_price, new_item['price'])
            if not valid_price:
                return False
            return match_sku
        else:
            return False
    else:
        return False

def brand_match(new_item):
    brand = new_item.get('brand', '').upper()
    brand_matches = brand == 'LEGO' or brand.startswith('LEGO ') \
        or 'LEGO' in new_item['name'].upper()
    return brand_matches

class BaseLegoAmazonSpider(BaseAmazonSpider):
    all_sellers = True

    download_delay = 1.0
    randomize_download_delay = True

    skus_found = []
    errors = []
    exclude_products = []

    lego_amazon_domain = 'www.amazon.com'

    def __init__(self, *args, **kwargs):
        super(BaseLegoAmazonSpider, self).__init__(self.lego_amazon_domain, *args, **kwargs)
        self._re_sku = re.compile(r'(\d{3,})')
        self.try_suggested = False
        self.do_retry = True

        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.old_skus = []
        if os.path.exists(self.f_skus_found):
            shutil.copy(os.path.join(HERE, self.f_skus_found),
                        os.path.join(HERE, '%s.bak' % self.f_skus_found))
            with open(self.f_skus_found) as f:
                for sku in f:
                    self.old_skus.append(sku.strip())

    def spider_closed(self, spider):
        missing_skus = set(self.old_skus) - set(self.skus_found)
        for sku in missing_skus:
            self.errors.append('WARNING: sku %s not found' % sku)
        with open(self.f_skus_found, 'w') as f:
            for sku in self.skus_found:
                f.write('%s\n' % sku)

    def match_min_price(self, search_item, new_item, price_diff=0.5):
        ''' Checks price variation '''
        search_price = search_item.get('price', None)
        if not search_price:
            return True
        search_price = Decimal(search_price)
        diff = Decimal(search_price) * Decimal(price_diff)
        matches = search_price - diff <= Decimal(new_item['price'])
        if not matches:
            self.log('Item price is too different from %s, reject %s' % (search_price, new_item))
        return matches

    def match_lego_name(self, search_item, new_item):
        sku = self._re_sku.findall(new_item['name'].replace(' ', ''))
        sku.extend(self._re_sku.findall(new_item['name']))
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
                valid_price = self._check_max_price(search_price, new_item['price'])
                if not valid_price:
                    self.log('Reject lot of products => %s' % new_item['url'])
                    return False
                return match_sku
            else:
                self.log('Reject lot of products => %s' % new_item['url'])
                return False

        return self.match_name(search_item, new_item, match_threshold=70)

    def match(self, search_item, new_item):
        return (self.match_min_price(search_item, new_item)
                and self.match_lego_name(search_item, new_item)
                and not self._excluded_product(new_item['name'])
                and self._valid_terms(new_item['name']))

    def basic_match(self, search_item, new_item):
        return self.match_lego_name(search_item, new_item)

    def _excluded_product(self, product_name):
        for product in self.exclude_products:
            if product.upper() in product_name.upper():
                return True
        return False

    def parse_mbc_list(self, response):
        hxs = HtmlXPathSelector(response)

        try:
            hxs.select('//a[@id="olpDetailPageLink"]/@href').extract()[0]
        except:
            yield self.retry_download(failure=None,
                                      url=response.url,
                                      metadata=response.meta,
                                      callback=self.parse_mbc_list)
        else:
            for r in super(BaseLegoAmazonSpider, self).parse_mbc_list(response):
                yield r

    def _collect_all(self, collected_items, new_item):
        if new_item['sku'] not in self.skus_found:
            self.skus_found.append(new_item['sku'])
        super(BaseLegoAmazonSpider, self)._collect_all(collected_items, new_item)

    def _collect_lowest_price(self, collected_items, new_item):
        if new_item['sku'] not in self.skus_found:
            self.skus_found.append(new_item['sku'])
        super(BaseLegoAmazonSpider, self)._collect_lowest_price(collected_items, new_item)

    def _collect_best_match(self, collected_items, new_item, search):
        if new_item['sku'] not in self.skus_found:
            self.skus_found.append(new_item['sku'])
        super(BaseLegoAmazonSpider, self)._collect_best_match(collected_items, new_item, search)

    def _check_max_price(self, search_price, price):
        ''' Checks price variation '''
        price_diff = 0.5
        search_price = Decimal(search_price)
        diff = Decimal(search_price) * Decimal(price_diff)
        return Decimal(price) <= search_price + diff

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
                    itsvalid = False
                    for e in exceptions:
                        if e.lower() in item_name:
                            itsvalid = True
                            break
                    if not itsvalid:
                        return False
        return True

