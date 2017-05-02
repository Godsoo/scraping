import re
import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand

from scrapy import log


HERE = os.path.abspath(os.path.dirname(__file__))


class TyresavingsSpider(BaseSpider):
    name = 'tyresavings.com_test'
    allowed_domains = ['tyresavings.com']
    start_urls = ('http://www.tyresavings.com/',)
    tyre_sizes = []
    brands = []
    all_man_marks = {}

    def __init__(self, *args, **kwargs):
        super(TyresavingsSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.brands = [row['Brand'] for row in self.tyre_sizes]

    def start_requests(self):
        for row in self.tyre_sizes:
            formdata = {}

            formdata['profile'] = row['Aspect Ratio']
            formdata['diameter'] = row['Rim']
            formdata['width'] = row['Width']
            formdata['speed'] = row['Speed rating']
                
            form_url = 'http://www.tyresavings.com/order/select-tyres-and-savings'
            yield FormRequest(form_url, dont_filter=True, formdata=formdata, meta={'row':row}, callback=self.parse)

            if row['Alt Speed']:
                formdata = {}

                formdata['profile'] = row['Aspect Ratio']
                formdata['diameter'] = row['Rim']
                formdata['width'] = row['Width']
                formdata['speed'] = row['Alt Speed']

                form_url = 'http://www.tyresavings.com/order/select-tyres-and-savings'
                yield FormRequest(form_url, dont_filter=True, formdata=formdata, meta={'row':row}, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
  
        row = response.meta['row']

        products = hxs.select('//div[@id="formcontent"]/div[@class="result"]')

        for product_el in products:
            loader = ProductLoader(item=Product(), selector=product_el)

            brand = product_el.select('p/span[@class="brand_text"]/text()').extract()
            brand = brand[0] if brand else ''

            winter_tyre = product_el.select('div/img[@title="Winter Tyre"]').extract()
            # skip winter tyres
            if winter_tyre:
                continue

            for tyre_brand in self.brands:
                if tyre_brand.upper() == brand.strip().upper():
                    brand = tyre_brand

            full_name = ''.join(product_el.select('p[@class="the_tyre"]/text()').extract()).strip()

            loader.add_value('name', ' '.join(full_name.split()[2:]))
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            identifier = product_el.select('p/span/select/@name').extract()
            if identifier:
                identifier = identifier[0].replace('number[', '').replace(']', '')
            else:
                log.msg('Product without identifier')
                search_params = '/'.join([row['Aspect Ratio'], row['Rim'], row['Width'], row['Alt Speed']])
                log.msg('Search parameters: ' + search_params)
                return

            loader.add_value('url', 'http://www.tyresavings.com')
            loader.add_xpath('image_url', 'img[@class="tyre_image"]/@src')
            loader.add_value('identifier', identifier)

            price = ''.join(product_el.select('div[@class="price"]/text()').extract()).strip()

            if not price:
                continue

            loader.add_value('price', price)

            metadata = MicheldeverMeta()

            metadata['aspect_ratio'] = row['Aspect Ratio']
            metadata['rim'] = row['Rim']

            speed = re.search('(\s\d+\w+\s)', full_name)
            speed_rating = speed.group().strip()[-1] if speed else ''
            load_rating = speed.group().strip()[:-1] if speed else ''

            metadata['speed_rating'] = speed_rating
            metadata['load_rating'] = load_rating

            metadata['width'] = row['Width']

            metadata['fitting_method'] = 'Fitted'
            metadata['alternative_speed_rating'] = ''
            xl = product_el.select('div/img[@title="Reinforced Tyre"]').extract()
            metadata['xl'] = 'Yes' if xl else 'No'
            run_flat = product_el.select('div/img[@title="Run Flat Tyre"]').extract()
            metadata['run_flat'] = 'Yes' if run_flat else 'No'

            metadata['manufacturer_mark'] = self._get_manufacturer_code(full_name)

            metadata['full_tyre_size'] = '/'.join((row['Width'],
                                                   row['Aspect Ratio'],
                                                   row['Rim'],
                                                   metadata['load_rating'],
                                                   metadata['speed_rating']))
            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            new_speed_rating = get_speed_rating(product)
            new_alt_speed = get_alt_speed(product)
            product['metadata']['alternative_speed_rating'] = new_alt_speed if new_alt_speed else \
                product['metadata']['speed_rating'] if product['metadata']['speed_rating'] != new_speed_rating else ''
            product['metadata']['speed_rating'] = new_speed_rating

            yield product

    def _get_manufacturer_code(self, name):
        name = name.upper()
        for code, manufacturer_mark in self.all_man_marks.items():
            if code not in name:
                continue

            if code in name.split(' ') or code == '*':
                return manufacturer_mark

        return ''

    def match_name(self, search_name, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold
