# -*- coding: utf-8 -*-
"""
    BaseeBaySpider
    ~~~~~~~~~~~~~~
    
    A base spider for eBay sites
    
"""


__author__ = 'Emiliano M. Rudenick'

import csv
import re
import json
from difflib import SequenceMatcher
from urlparse import urljoin

from decimal import Decimal
from urllib import urlencode
from itertools import combinations

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price2uk


class BaseeBaySpider(BaseSpider):
    ACCURACY = 50

    VALID_PERC = Decimal(0.4)

    # Search criteria
    DEFAULT_CRITERIA = -1
    ALL_ANY_ORDER = 1  # All words any order
    ANY_ANY_ORDER = 2  # Any words any order
    EXT_EXT_ORDER = 3  # Exact words exact order
    EXT_ANY_ORDER = 4  # Exact words any order

    allowed_domains = ['ebay.com', 'ebay.co.uk']

    # concurrent_items = 5000
    # download_delay = 0.15
    # concurrent_requests_per_domain = 3

    errors = []

    def __init__(self, *args, **kwargs):
        super(BaseeBaySpider, self).__init__(*args, **kwargs)
        self._ebay_url = 'http://www.ebay.co.uk/'
        self._csv_file = None
        self._exclude_sellers = []
        self._search_criteria = self.ALL_ANY_ORDER
        self._search_in_desc = False
        self._search_in_options = True
        self._search_params = {'_sop': '2',
                               '_fss': '1',
                               '_rusck': '1',
                               '_sacat': '0',
                               '_from': 'R40',
                               'LH_BIN': '1',
                               'LH_ItemCondition': '3',
                               'rt': 'nc'}
        self._search_fields = ['title']
        self._match_fields = ['sku']
        self._meta_fields = []
        self._format_fields = []
        self._check_valid_item = None
        self._all_vendors = True
        self._try_replacing = []
        self._check_diff_ratio = False
        self._ratio_accuracy = self.ACCURACY
        self._limit_pages = 0
        self._converted_price = False  # True for US$ in ebay.com case
        self._check_valid_currency = None  # callable to check if currency is valid
        self._extract_stock_amount = False  # whether spider should extract stock amount or not
        self._look_related = True
        self._look_related_not_items = False  # Look at related items when no items found

        self.__collected_items = set()

    def start_requests(self):
        with open(self._csv_file) as f:
            reader = csv.DictReader(f)
            # The longer sentences first
            items = sorted(reader,
                           key=lambda row: \
                            len(' '.join(row[field]
                                         for field in self._search_fields)),
                           reverse=True)
        number = 0
        for row in items:
            number += 1
            for field, func_format in self._format_fields:
                row[field] = func_format(row[field])
            meta = dict(dict((m_k, row[m_f].strip()) for m_k, m_f in self._meta_fields))
            search = ' '.join(row[field].strip() for field in self._search_fields)
            meta.update({'search': search})
            # Get URL
            search = self._clean_search(search)  # Clean search
            url = self._get_url_search(search)
            self.log('Item %s | SKU: %s | Search by: %s' % (number,
                                                            meta.get('sku', None),
                                                            search))
            yield self._search(url, meta)

    def _search(self, url, item_meta):
        meta = {'urls': [],
                'matching_items': [],
                'item_meta': item_meta}
        return Request(url, meta=meta, callback=self.parse_list, dont_filter=True)

    def _clean_search(self, search):
        return search

    def load_item(self, item, name, identifier, price, response):
        try:
            category = item.select('//td[@id="vi-VR-brumb-lnkLst"]//span[@itemprop="name"]/text()').extract().pop()
        except IndexError:
            category = ''
        seller_id = ''.join(item.select('.//*[contains(@class, "si-content")]'
                                        '//a/*[@class="mbg-nw"]/text()').extract())

        brand = response.meta['item_meta'].get('brand')
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Brand")]'
                            '/following-sibling::*[1]//text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Brand")]'
                            '/following-sibling::*[1]/h2/text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Brand")]'
                            '/following-sibling::*[1]/h3/text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Marke")]'
                            '/following-sibling::*[1]//text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Hersteller")]'
                            '/following-sibling::*[1]//text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Marque")]'
                            '/following-sibling::*[1]//text()').extract())
                
        product_loader = ProductLoader(item=Product(), selector=item)
        for field in self._match_fields:
            product_loader.add_value(field,
                                     response.meta['item_meta'].get(field, None))
        product_loader.add_value('name', name)
        product_loader.add_value('category', category)
        product_loader.add_value('dealer', 'eBay - ' + seller_id)
        product_loader.add_value('identifier', identifier)
        if brand:
            if type(brand) == list:
                product_loader.add_value('brand', brand[0])
            else:
                product_loader.add_value('brand', brand)
        product_loader.add_xpath('image_url', '//img[@id="icImg"]/@src')
        product_loader.add_value('url', item.response.url)
        price = price if price is not None else self._get_item_price(item)
        product_loader.add_value('price', price)

        # stock amount
        if self._extract_stock_amount:
            stock = ''
            try:
                in_stock = ''.join(item.select('//*[@id="qtySubTxt"]//text()').extract())
                stock = ''
                for match in re.finditer(r"([\d]+)", in_stock):
                    if len(match.group()) > len(stock):
                        stock = match.group()
                if 'More than' in in_stock:
                    stock = 11
            except:
                pass
            if stock:
                product_loader.add_value('stock', stock)

        # shipping cost
        try:
            shipping_cost = item.select('//*[@id="shippingSection"]//td/div/text()').extract()[0]
            if shipping_cost:
                if 'free' in shipping_cost.lower():
                    product_loader.add_value('shipping_cost', 0)
                else:
                    product_loader.add_value('shipping_cost', extract_price2uk(shipping_cost))
        except IndexError:
            pass

        return product_loader

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//div[@id="ResultSetItems"]//h3/a/@href').extract()

        if self._look_related:
            if not items or not self._look_related_not_items:
                items = hxs.select('//h3/a/@href').extract()

        if not items:
            url = hxs.select('//span[@class="seeAll"]/a/@href').extract()
            if url:
                listurl = urljoin(base_url, url[0])
                for param, value in self._search_params.items():
                    listurl = add_or_replace_parameter(listurl, param, value)
                # 200 items per page
                listurl = add_or_replace_parameter(listurl, '_ipg', '200')
                meta = response.meta['item_meta'].copy()
                yield self._search(listurl, meta)

        if not items:
            meta = response.meta['item_meta'].copy()
            search = meta['search']

            meta['new_queries'] = meta.get('new_queries', self._get_replacements_search(search))

            if meta['new_queries']:
                new_query = meta['new_queries'].pop(0)
                self.log('New query by: %s : %s' % (search, new_query))
                url = self._get_url_search(new_query)
                yield self._search(url, meta)
            else:
                self.log('No more queries')
        else:
            for item_url in items:
                self.log('Append URL %s' % (item_url))
                response.meta['urls'].append(item_url)

            next_page = hxs.select('//a[contains(@title, "Next page of results")]'
                                   '/@href').extract()
            if not next_page:
                next_page = hxs.select('//a[contains(@aria-label, "chste Seite mit Suchergebnissen")]'
                                   '/@href').extract()

            if next_page and 'javascript:;' not in next_page:
                try:
                    page = int(re.search(r'_pgn=(\d+)', next_page[0]).groups()[0])
                    if self._limit_pages <= 0 or (self._limit_pages > 0 and page < self._limit_pages):
                        self.log('Next page: %s' % (next_page[0]))
                        yield Request(next_page[0],
                                      callback=self.parse_list,
                                      meta=response.meta)
                    else:
                        self.log('LIMIT PAGES => %s < %s' % (page, self._limit_pages))
                except IndexError:
                    self.errors.append('LIMIT PAGE ERROR => %s' % (next_page[0]))
            else:
                self.log('Run products requests...')
                for obj in self._run_products_requests(response.meta):
                    yield obj

    def parse_product(self, response):
        meta = response.meta['item_meta'].copy()

        search = meta['search'].lower()

        hxs = HtmlXPathSelector(response)

        first_name = ' '.join(hxs.select('//*[@id="itemTitle"]/text()')
                              .extract()).strip()

        queries = [search]

        if self._try_replacing:
            queries.extend(self._get_replacements_search(search))

        self.log('Name: %s' % first_name)

        options_variations = []

        if self._search_in_options:
            try:
                json_var_map = unicode(hxs.select('//*/text()')
                                       .re(r'("menuItemMap":{.*}.*),'
                                           '"unavailableVariationIds"')[0])
            except:
                self.log('No item variations map...')
            else:
                json_var_map = re.sub(r',"watchCountMessage":".*?}', '}', json_var_map)
                variations = json.loads('{' + re.sub(r',"unavailableVariationIds".*', '', json_var_map) + '}')

                menu_map = variations['menuItemMap']

                for key, variation in variations['itemVariationsMap'].items():
                    if variation['traitValuesMap']:
                        new_variation = {}
                        for option, value in variation['traitValuesMap'].items():
                            new_variation[option] = menu_map[str(value)]['displayName']
                        price = variation['price']
                        if self._converted_price:
                            converted_price = variation.get('convertedPrice')
                            price = converted_price if converted_price else price
                        options_variations.append({'price': price,
                                                   'values': new_variation,
                                                   'identifier': key})

        item_ratio = 0
        item_name = first_name
        item_identifier = response.url.split('?')[0].split('/')[-1]
        item_price = None

        if options_variations and self._search_in_options:

            max_ratio = 0
            sel_model = {}

            for model in options_variations:
                for query in queries:
                    model_name = first_name + ' ' + \
                        ' '.join(opt_name.strip().lower()
                                 for o, opt_name in model['values'].items())

                    model_ratio = self._get_ratio(query, model_name)

                    if not max_ratio or model_ratio > max_ratio:
                        max_ratio = model_ratio
                        sel_model = {'name': model_name,
                                     'price': model['price'],
                                     'identifier': model['identifier']}

            try:
                item_ratio = max_ratio
                item_name = sel_model['name']
                item_price = sel_model['price']
                item_identifier = item_identifier + ':' + sel_model['identifier']
            except Exception, e:
                self.errors.append('ERROR: Error in search "%s" => %s' % (search, response.url))
                raise e
        elif self._check_diff_ratio:

            max_ratio = 0

            for query in queries:
                query_ratio = self._get_ratio(query, first_name)

                if query_ratio > max_ratio:
                    max_ratio = query_ratio

            item_ratio = max_ratio

        if item_ratio >= self._ratio_accuracy or not self._check_diff_ratio:
            item_loader = self.load_item(hxs, item_name, item_identifier, item_price, response)
            if item_identifier not in self.__collected_items:
                if self._valid_item(item_loader, response):
                    orig_price = meta.get('price')
                    is_valid_price = True if orig_price is None else False
                    price = item_loader.get_output_value('price')
                    if not is_valid_price and price is not None:
                        is_valid_price = self._valid_price(orig_price, price)
                    if is_valid_price and price is not None:
                        response.meta['matching_items'].append(item_loader.load_item())
                    else:
                        self.log('Ignoring result due to price %s (original price %s)'
                                 % (price, orig_price))

        for obj in self._run_products_requests(response.meta):
            yield obj

    def _run_products_requests(self, meta):
        if meta['urls']:
            url = meta['urls'].pop(0)
            self.log('Parse %s' % (url))
            yield Request(url, callback=self.parse_product, meta=meta, dont_filter=True)
        else:
            for item in self._collect_items(meta):
                yield item

    def _collect_items(self, meta):
        matching_items = meta['matching_items']
        if self._all_vendors:
            for item in matching_items:
                yield item
        elif matching_items:
            item = self._get_lowest_price_item(matching_items)
            self.__collected_items.add(item['identifier'])
            yield item

    def _get_url_search(self, search):
        params = self._search_params
        params.update({'_nkw': search,
                       '_odkw': search})
        if self._search_criteria != self.DEFAULT_CRITERIA:
            params.update({'_in_kw': str(self._search_criteria)})
        if self._search_in_desc:
            params.update({'LH_TitleDesc': '1'})
        if self._exclude_sellers:
            sellers = ' '.join(self._exclude_sellers)
            params.update({'_sasl': sellers,
                           'LH_SpecificSeller': '2..' + sellers})
        url = urljoin(self._ebay_url, 'dsc/i.html?%(params)s' %
                          ({'params': urlencode(params)}))
        return url

    def _get_item_price(self, item):
        try:
            price = item.select('//*[@id="prcIsum"]/text()').extract()[0].strip()
        except IndexError:
            try:
                price = item.select('//*[@id="mm-saleDscPrc"]/text()').extract()[0].strip()
            except IndexError:
                try:
                    price = re.search(r'"binPrice":".*[\$\xA3]([\d\.,]+)",', item.response.body).groups()[0]
                except AttributeError:
                    self.errors.append("Price not found for " + item.response.url)
                    return None
        # Converted price
        if self._converted_price:
            converted_price = item.select(u'//div[@id="prcIsumConv"]/span/text()').extract()
            price = converted_price[0] if converted_price else price
        if not price:
            return None
        if callable(self._check_valid_currency):
            currency = ''
            for char in price:
                if char.isdigit():
                    break
                currency += char
            if not self._check_valid_currency(currency):
                return None
        return extract_price2uk(price)

    def _valid_item(self, item, response):
        if callable(self._check_valid_item):
            if not self._check_valid_item(item, response):
                return False
        return True

    def _valid_price(self, orig_price, price):
        if callable(self._check_valid_price) and orig_price and price:
            return self._check_valid_price(Decimal(orig_price), Decimal(price))
        return True

    def _get_lowest_price_item(self, items):
        lowest_price = 0
        lowest_item = None
        for item in items:
            price = item['price']
            if lowest_price == 0 or price < lowest_price:
                lowest_price = price
                lowest_item = item
        return lowest_item

    def _get_replacements_search(self, search):
        search = search.lower()
        reduced = filter(lambda r: r[0].lower() in search, self._try_replacing)
        size = len(reduced)
        new_queries = []
        for i in range(size):
            sub_combinations = combinations(reduced, i + 1)
            for rplcs in sub_combinations:
                new_query = search
                for rplc in rplcs:
                    new_query = new_query.replace(rplc[0].lower(),
                                                  rplc[1].lower())
                new_queries.append(new_query)
        return list(set(new_queries))

    def _get_ratio(self, search, item_name):
        s1 = set(sorted([w.strip().lower()
                         for w in re.findall(r"[\w']+", search.lower())]))
        s2 = set(sorted([w.strip().lower()
                         for w in re.findall(r"[\w']+", item_name.lower())]))
        intersection = s1.intersection(s2)
        m = SequenceMatcher(None,
                            ' '.join(sorted(s1)),
                            ' '.join(sorted(intersection)))
        return int(m.ratio() * 100)

    def _check_valid_price(self, site_price, price):
        if not site_price:
            site_price = price
        p1 = Decimal(site_price)
        p2 = Decimal(price)

        return p1 - p1 * self.VALID_PERC <= p2 <= p1 + p1 * self.VALID_PERC

