from scrapy import Spider, Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from urlparse import urljoin
import itertools
from decimal import Decimal
from product_spiders.items import Product, ProductLoader
import re
import json
import os
import csv
from collections import defaultdict

HERE = os.path.abspath(os.path.dirname(__file__))


QTY_VALUES = [
    1, 2, 3, 4, 5, 10, 15, 25, 50, 100, 150,
    200, 250, 300, 400, 500, 600, 700, 750, 800,
    900, 1000, 1250, 1500, 1750, 2000, 2250, 2500,
    2750, 3000, 3500, 4000, 4500, 5000, 10000, 15000,
    20000, 25000, 30000, 40000, 50000]


class SoloPressSpider(Spider):
    name = 'instantprint-solopress.com'
    allowed_domains = ['solopress.com']
    start_urls = ['https://www.solopress.com']
    root_url = 'https://www.solopress.com'
    total = 0
    seen_options = defaultdict(set)
    handle_httpstatus_list = [502, 504]
    rotate_agent = True

    # download_timeout = 30

    max_deep = 3
    product_urls = set()

    cookie_no = 1

    RESTRICT = {
        'https://www.solopress.com/flyers-leaflets/square/':
        {
            'size': ['148 x 148', '210 x 210'],
            'bundling': ['no thank'],
            'paper type': ['silk', 'matt', 'gloss'],
            'weight': ['130', '150', '250', '350', '400'],
            'artwork': ['no thank']
        },
        'https://www.solopress.com/flyers-leaflets/a6/':
        {
            'finishing': ['none'],
            'size': ['a6'],
            'bundling': ['no thank'],
            'paper type': ['silk', 'matt', 'gloss'],
            'weight': ['130', '150', '250', '350', '400'],
            'artwork': ['no thank']
        },
        'https://www.solopress.com/flyers-leaflets/a7/':
        {
            'finishing': ['none'],
            'size': ['a7'],
            'bundling': ['no thank'],
            'paper type': ['silk', 'matt', 'gloss'],
            'weight': ['130', '150', '250', '350', '400'],
            'artwork': ['no thank']
        },
        'https://www.solopress.com/flyers-leaflets/a5/':
        {
            'finishing': ['none'],
            'size': ['a5'],
            'bundling': ['no thank'],
            'paper type': ['silk', 'matt', 'gloss'],
            'weight': ['130', '150', '250', '350', '400'],
            'artwork': ['no thank']
        },
        'https://www.solopress.com/flyers-leaflets/a4/':
        {
            'finishing': ['none'],
            'size': ['a4'],
            'bundling': ['no thank'],
            'paper type': ['silk', 'matt', 'gloss'],
            'weight': ['130', '150', '250', '350', '400'],
            'artwork': ['no thank']
        },
        'https://www.solopress.com/flyers-leaflets/a3/':
        {
            'finishing': ['none'],
            'size': ['a3'],
            'bundling': ['no thank'],
            'paper type': ['silk', 'matt', 'gloss'],
            'weight': ['130', '150', '250', '350', '400'],
            'artwork': ['no thank']
        },
        'https://www.solopress.com/flyers-leaflets/dl/':
        {
            'finishing': ['none'],
            'size': ['dl'],
            'bundling': ['no thank'],
            'paper type': ['silk', 'matt', 'gloss'],
            'weight': ['130', '150', '250', '350', '400'],
            'artwork': ['no thank']
        },
        'https://www.solopress.com/products/stapled-brochures/130gsm-silk-stapled-brochures/':
        {
            'size': ['a4', 'a5', 'a6'],
            'inside pages': ['130'],
            'cover': ['250'],
            'bundling': ['no thank'],
        }
    }

    def __init__(self, *args, **kwargs):
        super(SoloPressSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        self._identifiers = set()
        self._missing_requests = []

    def spider_idle(self, *args, **kwargs):
        if self._missing_requests:
            req = self._missing_requests.pop(0)
            self.crawler.engine.crawl(req, self)

    def parse(self, response):
        with open(os.path.join(HERE, 'solopress_cats.csv')) as f:
            reader = csv.reader(f)
            for prod_url, prod_name in reader:
                # For test purposes uncomment this and try the prefered product type
                if prod_name != 'Flyers & Leaflets': continue
                if prod_url not in self.RESTRICT:
                    self.RESTRICT[prod_url] = {'artwork': ['no thank'], 'bundling': ['no thank']}
                self.product_urls.add(prod_url)
                self.cookie_no += 1
                yield Request(prod_url,
                              meta={'product_name': prod_name,
                                    'product_url': prod_url,
                                    'cookiejar': self.cookie_no},
                              callback=self.parse_product)

    def _parse_product_features(self, product_data, url):
        product_features = {}
        for x in product_data['optionList']:
            if str(x['id']) == '1418':
                continue # ignore finishing options
            product_features[x['id']] = {'selected': x['defaultItem'], 'name': x['name']}
            options = []
            for r in x['viewableItems']:
                options.append({'name': r['name'], 'id': r['id']})
                if r['name'] == x['defaultItem']:
                    product_features[x['id']]['selected_id'] = r['id']
            product_features[x['id']]['options'] = options

        restrict = self.RESTRICT[url]
        for f in product_features:
            for r in restrict:
                if r in product_features[f]['name'].lower():
                    product_features[f]['options'] = [o for o in product_features[f]['options']
                                                      if any([c in o['name'].lower() for c in restrict[r]]) or
                                                      restrict[r] == ['*']]
        return product_features

    def _get_current_combination(self, product_data):
        combination = []
        for x in product_data['optionList']:
            default_item = x['defaultItem']
            selected_id = None
            for k in x['viewableItems']:
                if k['name'] == default_item:
                    selected_id = k['id']
            combination.append({str(x['id']): selected_id})

        return combination

    def _get_all_combinations(self, product_features):
        option_lists = []
        for f in product_features:
            option_lists.append([{str(f): x['id']} for x in product_features[f]['options']])

        option_combinations = itertools.product(*option_lists)
        return option_combinations

    def parse_product(self, response):
        try:
            js = re.search('productOptionsJSONRaw = \'(.*)\'', response.body).groups()[0]
            product_data = json.loads(js.replace('\\"', '"'))
        except:
            meta = response.meta
            retries = meta.get('retries_product', 0)
            if retries < 10:
                self.log('Retrying...')
                req = response.request.replace(dont_filter=True)
                req.meta['retries_product'] = retries + 1
                self._missing_requests.append(req)
        else:
            if 'retries_option' in response.meta:
                del response.meta['retries_option']
            for r in self.parse_option(response, product_data):
                yield r

    def parse_option(self, response, product_data=None):
        if response.status == 504 or response.status == 502:
            meta = response.meta
            retries = meta.get('retries_option', 0)
            if retries < 10:
                self.log('Retrying...')
                req = response.request.replace(dont_filter=True)
                req.meta['retries_option'] = retries + 1
                self._missing_requests.append(req)
            return
        if not product_data:
            product_data = json.loads(response.body)
        product_id = product_data['id']
        product_url = urljoin(self.root_url, product_data['productVariationURL'])
        if product_url not in self.product_urls and 'flyers-leaflets' not in product_url:
            self.product_urls.add(product_url)
            # Parse new product page, workarund to fix issue in Posters category
            self.cookie_no += 1
            new_meta = response.meta.copy()
            new_meta['variation_url'] = product_url
            new_meta['cookiejar'] = self.cookie_no
            if 'retries_product' in new_meta:
                del new_meta['retries_product']
            self._missing_requests.append(Request(product_url, meta=new_meta, callback=self.parse_product))
            return
        image_url = urljoin(self.root_url, product_data['variationThumbnailURL'])
        if u'\\u0026' in product_data['name']:
            product_data['name'] = product_data['name'].replace(u'\\u0026', u'&')
        name = product_data['name']
        combination = self._get_current_combination(product_data)
        metadata = {}
        for x in product_data['optionList']:
            if 'no thank' not in x['defaultItem'].lower():
                name += u' - {}: {}'.format(x['name'], x['defaultItem'])
            if x['name'] == 'Number of Pages':
                n_pages = re.findall(r'(\d+)', x['defaultItem'])
                if n_pages:
                    metadata['PrintPageNumber'] = n_pages[0]

        identifier = str(product_id)
        selected_combo = response.meta.get('combo')
        for c in combination:
            for k in c:
                identifier += '-{}_{}'.format(k, c[k])
        dont_extract = False
        if selected_combo is not None:
            for c in selected_combo:
                for k in c:
                    if '{}_{}'.format(k, c[k]) not in identifier:
                        self.log('WRONG COMBINATION!!!')
                        dont_extract = True

        if not dont_extract:
            if identifier not in self._identifiers:
                self._identifiers.add(identifier)
            else:
                return
            for q in product_data['defaultQuantities']:
                if int(q) not in QTY_VALUES:
                    continue
                metadata['ProdQty'] = str(q)
                loader = ProductLoader(item=Product(), response=response)
                opt_identifier = identifier + '_' + str(q)
                opt_name = name + ' - ' + str(q)
                price = product_data['defaultQuantities'][q]['netPrice']
                price = Decimal(price)
                if not 'gloss laminated' in opt_name.lower() and not 'matt laminated' in opt_name.lower():
                    price = (price / Decimal('1.2')).quantize(Decimal('0.01'))
                loader.add_value('identifier', opt_identifier)
                loader.add_value('name', opt_name)
                loader.add_value('price', str(price))
                loader.add_value('category', product_data['name'])
                loader.add_value('url', product_url)
                loader.add_value('image_url', image_url)
                item = loader.load_item()
                item['metadata'] = metadata
                yield item

        current_deep = int(response.meta.get('current_deep', 1))
        if current_deep >= self.max_deep:
            return

        product_features = self._parse_product_features(product_data, response.meta['product_url'])
        option_combinations = self._get_all_combinations(product_features)

        for c in option_combinations:
            if str(c) in self.seen_options[str(product_id)]:
                continue
            else:
                self.log('Combination not found {}'.format(str(c)))
                self.seen_options[str(product_id)].add(str(c))

            form_vals = {"productID": int(product_id), "productSelectionUID": ""}
            for op in c:
                form_vals.update(op)

            data = {"authenticityToken": 'cbd3561bda7c135b00ec86d43213fe1a0e23688d',
                    "formVals": form_vals}

            cookies = {'PLAY_SESSION': "5ea80d3df3ff155dd6c5f567833e9b6f9a8746d5-___AT=cbd3561bda7c135b00ec86d43213fe1a0e23688d&basket.id=15248198"}
            fr = Request(url='https://www.solopress.com/productfront/getupdatedproductoptions.json',
                         method='POST',
                         body=json.dumps(data), callback=self.parse_option,
                         cookies=cookies,
                         meta={'product_name': response.meta['product_name'],
                               'product_url': response.meta['product_url'],
                               'current_deep': current_deep + 1,
                               'cookiejar': response.meta['cookiejar'],
                               'combo': c,
                               'dont_retry': True},)
            self._missing_requests.append(fr)
