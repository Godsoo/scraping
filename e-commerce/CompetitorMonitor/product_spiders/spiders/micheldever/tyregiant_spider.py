import re
import os
import csv
import json
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))


class TyreGiantSpider(BaseSpider):
    name = 'tyregiant.com'
    allowed_domains = ['tyregiant.com', 'tyresavings.com']
    start_urls = ('http://www.tyresavings.com',)
    tyre_sizes = []
    brands = []
    manually_matched = []
    all_man_marks = {}

    download_delay = 0.1

    def __init__(self, *args, **kwargs):
        super(TyreGiantSpider, self).__init__(*args, **kwargs)
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

        self.search_history = set()

        self.finished = False

        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def _get_history_key(self, search_params):
        key = "%(width)s-%(rim)s-%(aspect_ratio)s-%(speed_rating)s" % search_params
        return key

    def check_in_history(self, search_params):
        if self._get_history_key(search_params) in self.search_history:
            return True
        return False

    def add_to_history(self, search_params):
        self.search_history.add(self._get_history_key(search_params))

    def spider_idle(self, spider):
        if not self.finished:
            request = Request(self.start_urls[0], dont_filter=True, callback=self.parse)
            self._crawler.engine.crawl(request, self)
            raise DontCloseSpider

    def parse(self, response):
        for r in self.next_search():
            yield r

    def next_search(self):
        request_sent = False
        for i, row in enumerate(self.tyre_sizes, 1):
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

                self.log("Checking row: %s" % str({
                    'width': row['Width'],
                    'aspect_ratio': row['Aspect Ratio'],
                    'speed_rating': row['Speed rating'],
                    'rim': row['Rim']
                }))

                self.add_to_history(search_params)

                url = 'http://www.tyresavings.com/%(width)s-%(aspect_ratio)s-%(rim)s?speed=%(speed_rating)s' % \
                      search_params
                yield Request(url, dont_filter=True, meta={'search_params': search_params}, callback=self.parse_search)
                request_sent = True
                break
            if request_sent:
                break
        else:
            self.finished = True
            return

    def parse_search(self, response):
        meta = response.meta
        url = 'http://www.tyresavings.com/update-tyres/1'
        meta['page'] = 1
        yield Request(url, dont_filter=True, callback=self.parse_products, meta=meta)

    def parse_products(self, response):
        html_response = json.loads(response.body)['display_tyres']
        hxs = HtmlXPathSelector(text=html_response)

        search_params = response.meta['search_params']

        products = hxs.select('//div[contains(@class, "tyre_container") and @id]')

        for product_el in products:
            loader = ProductLoader(item=Product(), selector=product_el)

            brand = product_el.select('.//span[@class="tyre_brand_text"]/text()').extract()
            brand = brand[0] if brand else ''

            winter_tyre = product_el.select('.//i[@class="icon-select_tyres-winter"]').extract()
            if not winter_tyre:
                for tyre_brand in self.brands:
                    if tyre_brand.upper() == brand.strip().upper():
                        brand = tyre_brand
                full_name = product_el.select('.//p[@class="tyre_details"]/span/text()').extract()[0]

                loader.add_value('name', full_name)
                loader.add_value('brand', unify_brand(brand))
                loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
                identifier = product_el.select('@id').extract()
                loader.add_value('identifier', identifier)

                loader.add_value('url', 'http://www.tyresavings.com')

                image_url = product_el.select('.//img[contains(@class, "tyre_image")]/@src').extract()

                if image_url:
                    loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))

                price = ''.join(product_el.select('.//*[@class="tyre_price"]//text()').re(r'[\d,.]+'))

                if not price:
                    loader.add_value('stock', 0)

                loader.add_value('price', price)

                metadata = MicheldeverMeta()
                metadata['aspect_ratio'] = search_params['aspect_ratio']
                metadata['rim'] = search_params['rim']

                tyre_details = product_el.select('.//*[@class="tyre_details"]/text()').extract()[0].strip()
                speed = re.search('(\s\d+\w+)', tyre_details)
                load_rating = speed.group().strip()[:-1] if speed else ''
                speed_rating = speed.group().strip()[-1] if speed else ''

                metadata['speed_rating'] = speed_rating
                metadata['load_rating'] = load_rating

                metadata['width'] = search_params['width']

                metadata['fitting_method'] = 'Fitted'
                metadata['alternative_speed_rating'] = ''
                xl = product_el.select('.//i[@class="icon-select_tyres-xl"]').extract()
                metadata['xl'] = 'Yes' if xl else 'No'
                run_flat_found = is_run_flat(full_name)
                run_flat = product_el.select('.//i[@class="icon-select_tyres-runflat"]').extract()
                metadata['run_flat'] = 'Yes' if run_flat or run_flat_found else 'No'

                metadata['manufacturer_mark'] = self._get_manufacturer_code(full_name)

                metadata['full_tyre_size'] = '/'.join((search_params['width'],
                                                       search_params['aspect_ratio'],
                                                       search_params['rim'],
                                                       metadata['load_rating'],
                                                       metadata['speed_rating']))
                fuel, grip, noise = filter(lambda s: bool(s),
                    map(unicode.strip,
                        product_el.select('.//div[@class="label_ratings"]//span[contains(@class, "label_rating_")]/text()|'
                                          './/div[@class="label_ratings"]//p[span[contains(@class, "decibels")]]/text()')
                        .extract()))

                metadata['fuel'] = fuel
                metadata['grip'] = grip
                metadata['noise'] = noise

                product = loader.load_item()
                product['metadata'] = metadata

                if not is_product_correct(product):
                    continue

                product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

                yield product

        if products:
            meta = response.meta
            next_page = meta['page'] + 1
            next_url = 'http://www.tyresavings.com/update-tyres/%s' % str(next_page)
            meta['page'] = next_page
            yield Request(next_url, dont_filter=True, callback=self.parse_products, meta=meta)

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
