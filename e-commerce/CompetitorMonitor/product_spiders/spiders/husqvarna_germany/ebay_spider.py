import os
import re
import csv

import json

from scrapy.selector import HtmlXPathSelector
from scrapy import log

from product_spiders.base_spiders import BaseeBaySpider
from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from product_spiders.config import DATA_DIR


class HusqvarnaDEEbaySpider(BaseeBaySpider):

    HERE = os.path.abspath(os.path.dirname(__file__))

    name = 'husqvarna-germany-ebay.de'
    download_delay = 0.1

    main_website_id = 983

    def __init__(self, *args, **kwargs):
        super(HusqvarnaDEEbaySpider, self).__init__()
        self._ebay_url = 'http://www.ebay.de'
        self._search_fields = ['brand', 'sku']
        self._all_vendors = True
        self._meta_fields = [('name', 'name'),
                             ('price', 'price'),
                             ('brand', 'brand'),
                             ('category', 'category')]
        self._match_fields = ('sku',)
        self._check_valid_item = self.__valid_item_
        self._converted_price = False
        self._check_diff_ratio = True
        self._re_sku = re.compile(r'(\d{3,})')
        self._look_related = False

        self.__collected_items = set()

        self._check_diff_ratio = True
        self.matcher = Matcher(self.log)

    def match_text(self, text, item_field, match_threshold=90, important_words=None):
        return True

    def start_requests(self):
        # assign main site's last crawl results to self._csv_file
        try:
            self._csv_file = os.path.join(DATA_DIR, '{}_products.csv'.format(self.main_website_last_crawl_id))
        except AttributeError:
            msg = "Couldn't find latest crawl for main spider (id={})".format(self.main_website_id)
            self.errors.append(msg)
            self.log(msg, level=log.CRITICAL)
            self.close(self, msg)
            return
        else:
            self.log("Found main spider's previous crawl results")

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
                meta = dict(dict((m_k, row[m_f]) for m_k, m_f in self._meta_fields))
                search = ' '.join(row[field].strip() for field in self._search_fields)

                meta.update({'search': search})
                # Get URL
                search = self._clean_search(search)  # Clean search
                url = self._get_url_search(search)
                self.log('Item %s | SKU: %s | Search by: %s' % (number,
                                                                meta.get('sku', None),
                                                                search))
                yield self._search(url, meta)

    def __valid_item_(self, item_loader, response):
        item_name = item_loader.get_output_value('name').lower()
        brand = response.meta['item_meta'].get('brand')
        if brand.upper().strip() in item_name.upper().strip():
            return True
        return False

    def load_item(self, item, name, identifier, price, response):
        try:
            category = item.select('//*[@id="vi-VR-brumb-lnkLst"]//a/text()').extract().pop()
        except IndexError:
            category = ''
        seller_id = ''.join(item.select('.//*[contains(@class, "si-content")]'
                                        '//a/*[@class="mbg-nw"]/text()').extract())

        brand = response.meta['item_meta'].get('brand')
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Brand")]'
                            '/following-sibling::*[1]/text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Brand")]'
                            '/following-sibling::*[1]/h2/text()').extract())
        if not brand:
            brand = filter(lambda s: s.strip() != '',
                item.select('//*[@class="attrLabels" and contains(text(), "Brand")]'
                            '/following-sibling::*[1]/h3/text()').extract())

        product_loader = ProductLoader(item=Product(), selector=item)
        for field in self._match_fields:
            product_loader.add_value(field,
                                     response.meta['item_meta'].get(field, None))
        product_loader.add_value('name', name)
        product_loader.add_value('category', category)
        product_loader.add_value('dealer', 'eBay - ' + seller_id)
        product_loader.add_value('identifier', identifier)

        sku = item.select('//tr[td[contains(text(), "Modell")]]/td/span/text()').extract()
        sku = sku[-1] if sku else ''
        product_loader.add_value('sku', sku)
        if brand:
            if type(brand) == list:
                product_loader.add_value('brand', brand[0])
            else:
                product_loader.add_value('brand', brand)
        product_loader.add_xpath('image_url', '//img[@id="icImg"]/@src')
        product_loader.add_value('url', item.response.url)
        price = extract_price(price) if price is not None else self._get_item_price(item)
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
                    product_loader.add_value('shipping_cost', extract_price(shipping_cost))
        except IndexError:
            pass

        return product_loader

    def _check_name_valid(self, name):
        return True

    def _check_category_valid(self, category):
        return True

    def _check_valid_price(self, site_price, price):
        ''' Checks price variation '''
        return True

    def parse_product(self, response):
        meta = response.meta['item_meta'].copy()

        search = meta['search'].lower()

        hxs = HtmlXPathSelector(response)

        condition_new = 'NEU' in ''.join(hxs.select('//div[@id="vi-itm-cond"]/text()').extract()).upper().strip()

        if not condition_new:
            return

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
        return extract_price(price)
