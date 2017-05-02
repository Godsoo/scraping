import re
import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest, Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand, is_run_flat

from scrapy import log


HERE = os.path.abspath(os.path.dirname(__file__))


class TyresavingsSpider(BaseSpider):
    name = 'tyresavings.com'
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

            size_page = row['Width'] + '-' + row['Aspect Ratio'] + '-' + row['Rim'] + '?speed=' + row['Speed rating'] + '&brand=' + row['Brand'].lower()
            yield Request('http://www.tyresavings.com/' + size_page, dont_filter=True, meta={'row':row}, callback=self.parse)

            # form_url = 'http://www.tyresavings.com/enter-size-submit'
            # yield FormRequest(form_url, dont_filter=True, formdata=formdata, meta={'row':row}, callback=self.parse)

            if row['Alt Speed']:
                formdata = {}

                # formdata['profile'] = row['Aspect Ratio']
                # formdata['diameter'] = row['Rim']
                # formdata['width'] = row['Width']
                # formdata['speed'] = row['Alt Speed']
                size_page = row['Width'] + '-' + row['Aspect Ratio'] + '-' + row['Rim'] + '?brand=' + row['Brand']
                # form_url = 'http://www.tyresavings.com/enter-size-submit'
                # yield FormRequest(form_url, dont_filter=True, formdata=formdata, meta={'row':row}, callback=self.parse)
                yield Request('http://www.tyresavings.com/' + size_page, dont_filter=True, meta={'row':row}, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        row = response.meta['row']

        products = hxs.select('//div[contains(@class, "tyre_container")]')

        for product_el in products:
            loader = ProductLoader(item=Product(), selector=product_el)

            brand = product_el.select('form/span[@class="tyre_brand_text"]/text()').extract()
            brand = brand[0] if brand else ''

            winter_tyre = product_el.select('div[@class="tyre_type"]/div[@class="tyre_winter"]').extract()
            # skip winter tyres
            if winter_tyre:
                continue

            for tyre_brand in self.brands:
                if tyre_brand.upper() == brand.strip().upper():
                    brand = tyre_brand

            full_name = ' '.join(map(lambda x: x.strip(), product_el.select('form/p[@class="tyre_details"]//text()').extract()))
            if not full_name:
                continue

            loader.add_value('name', ' '.join(full_name.split()[2:]))
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            identifier = product_el.select('@id').extract()
            if identifier:
                identifier = identifier[0]
            else:
                log.msg('Product without identifier')
                search_params = '/'.join([row['Aspect Ratio'], row['Rim'], row['Width'], row['Alt Speed']])
                log.msg('Search parameters: ' + search_params)
                return

            loader.add_value('url', response.url)
            image_url = product_el.select('img[contains(@class, "tyre_image")]/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            loader.add_value('identifier', identifier)

            price = ''.join(product_el.select('div/p[@class="tyre_price"]//text()').extract())

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
            xl = product_el.select('div[@class="tyre_type"]/div[@class="tyre_xl"]').extract()
            metadata['xl'] = 'Yes' if xl else 'No'
            run_flat_found = is_run_flat(full_name)
            run_flat = product_el.select('div[@class="tyre_type"]/div[@class="tyre_rf"]').extract()
            metadata['run_flat'] = 'Yes' if run_flat or run_flat_found else 'No'

            metadata['manufacturer_mark'] = self._get_manufacturer_code(full_name)

            metadata['full_tyre_size'] = '/'.join((row['Width'],
                                                   row['Aspect Ratio'],
                                                   row['Rim'],
                                                   metadata['load_rating'],
                                                   metadata['speed_rating']))

            fuel = product_el.select('.//div[@class="label_ratings"]/div[@class="fuel_rating"]//span[contains(@class, "label_rating_")]/text()').extract()
            grip = product_el.select('.//div[@class="label_ratings"]/div[@class="wet_rating"]//span[contains(@class, "label_rating_")]/text()').extract()
            noise = product_el.select('.//div[@class="label_ratings"]/div[contains(@class, "noise_rating")]/@data-decibels').extract()
            metadata['fuel'] = fuel[0] if fuel else ''
            metadata['grip'] = grip[0] if grip else ''
            metadata['noise'] = noise[0] if noise else ''

            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            yield product

        brand_filters = hxs.select('//div[@class="filter-wrapper"]/div[div/input[@name="brand_filter"]]/p/text()').extract()
        for brand_filter in brand_filters:
            url = response.url.split('&')[0] + '&brand=' + brand_filter.lower()
            yield Request(url, meta=response.meta, callback=self.parse)

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
