import re
import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest

from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, \
    get_speed_rating, get_alt_speed, find_brand_segment, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))

MANUFACTURER_MARKS = {'K1': 'K1',
                      'K2': 'K1',
                      'C1': 'C1',
                      'N0': 'NO',
                      'N1': 'NO',
                      'N2': 'NO',
                      'N3': 'NO',
                      'N4': 'NO',
                      'N5': 'NO',
                      'N6': 'NO',
                      '*': '*',
                      'RO1': 'R01',
                      'R02': 'R01',
                      'M0': 'M0',
                      'MO': 'M0',
                      'M02': 'M0',
                      'AO': 'A0',
                      'EZ': 'A0',
                      'VO': 'V0',
                      'A': 'A',
                      'ST': 'ST',
                      'B': 'B',
                      'B1': 'B',
                      'J': 'J'}


class ValueTyresSpider(BaseSpider):
    name = 'valuetyres.co.uk_test'
    allowed_domains = ('valuetyres.co.uk',)
    start_urls = ('http://www.valuetyres.co.uk/', )

    tyre_sizes = []
    all_man_marks = {}
    custom_man_marks = {}

    def _get_manufacturer_code(self, name):
        name = name.upper()
        for code, manufacturer_mark in self.all_man_marks.items():
            if code not in name:
                continue

            if code in name.split(' ') or code == '*':
                return manufacturer_mark

        return ''

    def __init__(self, *args, **kwargs):
        super(ValueTyresSpider, self).__init__(*args, **kwargs)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        self.errors = []

        self.search_history = set()

    def _get_history_key(self, search_params):
        key = "%(width)s-%(rim)s-%(aspect_ratio)s-%(speed_rating)s" % search_params
        return key

    def check_in_history(self, search_params):
        if self._get_history_key(search_params) in self.search_history:
            return True
        return False

    def add_to_history(self, search_params):
        self.search_history.add(self._get_history_key(search_params))

    def parse(self, response):
        for i, row in enumerate(self.tyre_sizes):
            for speed_rating in [row['Speed rating'], row['Alt Speed']]:
                if not speed_rating:
                    continue

                search_params = {
                    'width': row['Width'],
                    'aspect_ratio': row['Aspect Ratio'],
                    'speed_rating': speed_rating,
                    'rim': row['Rim']
                }

                if self.check_in_history(search_params):
                    continue

                self.add_to_history(search_params)

                formdata = {
                    'tyrewidth': search_params['width'],
                    'profile': search_params['aspect_ratio'],
                    'diameter': search_params['rim'],
                    'speed': search_params['speed_rating']
                }

                r = FormRequest.from_response(response, formname='frm-search',
                                              formdata=formdata,
                                              meta={
                                                  'cookiejar': i,
                                                  'speed_rating': speed_rating,
                                                  'search_params': search_params
                                              },
                                              callback=self.parse_products,
                                              dont_filter=True)
                yield r

    def parse_products(self, response):
        search_params = response.meta['search_params']

        formdata = {
            'viewall': '1',
            'width': search_params['width'],
            'profile': search_params['aspect_ratio'],
            'diameter': search_params['rim'],
            'speed': search_params['speed_rating'],
            'categoryname': '',
            'brand': '0',
            'filterbrands': '',
            'sortprice': 'price_asc'
        }

        r = FormRequest('http://www.valuetyres.co.uk/getitems',
                        formdata=formdata,
                        meta=response.meta,
                        callback=self.parse_products_data,
                        dont_filter=True)
        yield r

    def parse_products_data(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="mod-item-body"]/..')

        self.log('%s products found' % len(products))
        for product in products:
            desc = product.select('.//.//div[@class="mod-item-body"]/p//text()').extract()[0]
            if 'snow' in desc or 'winter' in desc:
                continue
            yield self.parse_product(product, fitted=True, search_params=response.meta['search_params'])
            # do not collect "Delivered" tyres
            # yield self.parse_product(product, fitted=False, search_params=response.meta['search_params'])

    def parse_product(self, product, fitted, search_params):
        url = product.select('.//div[@class="mod-item-body"]/h3//a/@href').extract()[0]
        p_id = url.split('/')[-1]
        p_id += '-F' if fitted else '-D'
        image_url = product.select('.//div[@class="mod-item-img"]//img/@src').extract()[0]
        brand = product.select('.//div[@class="mod-item-body"]/h3/text()').extract()[0].strip()
        try:
            if not fitted:
                price = product.select('.//div[@class="mod-delivered"]/a/text()').extract()[0]
            else:
                price = product.select('.//div[@class="mod-fitted"]/a/text()').extract()[0]
        except IndexError:
            self.log("Price not found: %s" % str(product))
            self.errors.append("Price not found: %s" % str(product))
            return

        name = product.select('.//div[@class="mod-item-body"]/h3/span/a/text()').extract()[0]

        pattern = re.sub('\d+[^\s]+R\d+', '', name)
        pattern = re.sub('[\d/]+%s' % search_params['speed_rating'].upper(), '', pattern)
        pattern = pattern.strip()
        if not pattern:
            pattern = name.strip()

        loader = ProductLoader(item=Product(), selector=product)
        loader.add_value('url', url)
        loader.add_value('identifier', p_id)
        loader.add_value('image_url', image_url)
        loader.add_value('brand', unify_brand(brand))
        loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
        loader.add_value('price', price)

        pattern = pattern.upper()
        pattern = pattern.replace('XL', '').replace('RFLAT', '').replace('RUNFLAT', '')

        loader.add_value('name', pattern)

        m = MicheldeverMeta()
        m['aspect_ratio'] = search_params['aspect_ratio']
        m['rim'] = search_params['rim']
        m['width'] = search_params['width']
        m['speed_rating'] = search_params['speed_rating'].upper()
        res = re.search('([\d/]+)%s' % search_params['speed_rating'].upper(), name)
        if res:
            m['load_rating'] = res.groups()[0]
        else:
            self.log('ERROR: not load rating: %s' % url)
            m['load_rating'] = ''
        if 'RFLAT' in name.upper() or 'RUNFLAT' in name.upper():
            m['run_flat'] = 'Yes'
        else:
            m['run_flat'] = 'No'

        if 'XL' in name.upper():
            m['xl'] = 'Yes'
        else:
            m['xl'] = 'No'

        m['full_tyre_size'] = '/'.join((m['width'],
                                        m['aspect_ratio'],
                                        m['rim'],
                                        m['load_rating'],
                                        m['speed_rating']))
                                        #m['alternative_speed_rating']))

        m['fitting_method'] = 'Fitted' if fitted else 'Delivered'
        m['manufacturer_mark'] = self._get_manufacturer_code(name)

        product = loader.load_item()
        product['metadata'] = m

        if not is_product_correct(product):
            return

        product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

        new_speed_rating = get_speed_rating(product)
        new_alt_speed = get_alt_speed(product)
        product['metadata']['alternative_speed_rating'] = new_alt_speed if new_alt_speed else \
            product['metadata']['speed_rating'] if product['metadata']['speed_rating'] != new_speed_rating else ''
        product['metadata']['speed_rating'] = new_speed_rating

        return product
