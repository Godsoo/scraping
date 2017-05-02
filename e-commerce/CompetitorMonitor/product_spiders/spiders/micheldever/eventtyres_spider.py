# -*- coding: utf-8 -*-

import re
import os
import csv
from scrapy import Spider, Request, FormRequest
from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader
from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, \
    find_brand_segment, unify_brand, is_run_flat
from decimal import Decimal


HERE = os.path.abspath(os.path.dirname(__file__))


brands_substitute = {
    'GT RADIAL': 'GT',
    'GAJAH TUNGAL': 'GT',
    'GAJAH TUNGGAL': 'GT',
    'RUNWAY': 'ENDURO',
}


class EvenTyresSpider(Spider):
    name = 'event-tyres.co.uk'
    allowed_domains = ['event-tyres.co.uk']

    website_url = 'http://www.event-tyres.co.uk/'
    postal_code = 'WA5 7ZB'
    price_discount = False  # extract multiple tyre discount price?

    def __init__(self, *args, **kwargs):
        super(EvenTyresSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        self.tyre_sizes = []
        self.all_man_marks = {}
        self.manually_matched = []

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                new_row = row.copy()
                self.tyre_sizes.append(new_row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.errors = []

    def start_requests(self):
        for i, row in enumerate(self.tyre_sizes):
            yield Request(self.website_url, callback=self.next_search,
                          meta={'row': row, 'cookiejar': str(i)}, dont_filter=True)

    def next_search(self, response):
        form_token = response.xpath('//input[@id="search_form__token"]/@value').extract()[0]
        row = response.meta['row']
        params = {'search_form[width]': row['Width'],
                  'search_form[profile]': row['Aspect Ratio'],
                  'search_form[size]': row['Rim'],
                  'search_form[postcode]': self.postal_code,
                  'search_form[_token]': form_token,
                  'search_form[search]': '',}
        r = FormRequest(url=self.website_url,
                        meta={'cookiejar': response.meta['cookiejar']},
                        formdata=params)
        yield r

    def parse(self, response):
        pages = set(response.xpath('//*[contains(@class, "pagination__item")]/a[not(contains(@class, "pagination__current"))]/@href').extract())
        for page_url in pages:
            yield Request(response.urljoin(page_url), meta=response.meta)

        products = response.xpath('//article[@itemtype="http://schema.org/Product"]')

        for product_el in products:
            loader = ProductLoader(item=Product(), selector=product_el)

            brand = product_el.xpath('.//*[@itemprop="brand"]//*[@itemprop="name"]/text()').extract()[0].strip()
            if brand.upper() in brands_substitute:
                brand = brands_substitute[brand.upper()]
            full_name = product_el.xpath('.//*[contains(@class, "product__title") and @itemprop="name"]/text()').extract()[0]
            try:
                tyre_size, name = re.split(brand, full_name, flags=re.I)
            except ValueError:
                self.log("[[TESTING]] Can not split tyre '%s' with brand '%s'" % (full_name, brand))
                continue
            # tyre_size, name = full_name.split(brand)
            loader.add_value('name', name)

            winter_tyre = product_el.xpath('.//*[@class="product__info"]//*[@data-icon="S" and contains(text(), "Winter")]')
            if not winter_tyre:
                loader.add_value('brand', unify_brand(brand))
                loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
                identifier = self.get_identifier(product_el)

                out_of_stock = product_el.xpath('.//*[@itemprop="availability" and contains(@content, "Out")]')
                if out_of_stock:
                    loader.add_value('stock', 0)

                loader.add_value('url', response.url)

                image_url = product_el.xpath('.//img[@itemprop="image"]/@src').extract()

                if image_url:
                    loader.add_value('image_url', response.urljoin(image_url[0]))

                loader.add_value('identifier', identifier)
                price = product_el.xpath('@data-price').extract()[0]
                loader.add_value('price', price)

                metadata = MicheldeverMeta()
                res = parse_pattern(tyre_size)
                if not res:
                    continue
                width, ratio, rim, load_rating, speed_rating = res
                metadata['aspect_ratio'] = ratio
                metadata['rim'] = rim
                metadata['speed_rating'] = speed_rating
                metadata['load_rating'] = load_rating
                metadata['width'] = width

                metadata['fitting_method'] = 'Fitted'
                metadata['alternative_speed_rating'] = ''
                xl = bool(product_el.xpath('.//*[@class="product__info"]//*[@data-icon="XL"]'))
                metadata['xl'] = 'Yes' if xl else 'No'
                run_flat_found = is_run_flat(full_name)
                run_flat = bool(product_el.xpath('.//*[@class="product__info"]//*[@data-icon="RF"]'))
                if not run_flat:
                    run_flat = ' RFT' in name
                metadata['run_flat'] = 'Yes' if run_flat or run_flat_found else 'No'

                man_code = self._get_manufacturer_code(full_name)

                metadata['manufacturer_mark'] = man_code

                metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                       metadata['aspect_ratio'],
                                                       metadata['rim'],
                                                       metadata['load_rating'],
                                                       metadata['speed_rating']))

                try:
                    fuel, grip, noise = product_el.xpath('.//li[contains(@class, "product__meta-item--")]/text()').extract()
                except:
                    fuel, grip, noise = ('', '', '')

                metadata['fuel'] = fuel
                metadata['grip'] = grip
                metadata['noise'] = noise

                product = loader.load_item()
                # The website is defaulting to 2 tyres with a discount of £10
                if product.get('price') and (not self.price_discount):
                    product['price'] += Decimal('10')
                product['metadata'] = metadata

                if not is_product_correct(product):
                    continue

                product['metadata']['mts_stock_code'] = self.find_mts_stock_code(product)

                yield product

    # Please don't remove this method. This method is overridden by the children.
    def find_mts_stock_code(self, product):
        return find_mts_stock_code(product, spider_name=self.name, log=self.log)

    # Please don't remove this method. This method is overridden by the children.
    def get_identifier(self, selector):
        return selector.xpath('@data-product').extract()[0]

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

tyre_pattern_regex = re.compile(r"(\d*)/(\d+\.?\d*)Z?[R|T]?(\d*) \(?([\d/]*)([a-zA-Z]{1})\)?")

def parse_pattern(pattern):
    """
    >>> parse_pattern('205/55R16 91V')
    ('205', '55', '16', '91', 'V')
    >>> parse_pattern('255/35R19 96Y')
    ('255', '35', '19', '96', 'Y')
    >>> parse_pattern('215/40R18 89W')
    ('215', '40', '18', '89', 'W')
    >>> parse_pattern('205/55R16 91V ')
    ('205', '55', '16', '91', 'V')
    >>> parse_pattern('215/65R16 102/100H ')
    ('215', '65', '16', '102/100', 'H')
    >>> parse_pattern('225/45ZR17 92Y ')
    ('225', '45', '17', '92', 'Y')
    >>> parse_pattern(' 225/40ZR18 (92Y) ')
    ('225', '40', '18', '92', 'Y')
    >>> parse_pattern('185/65T15 88T ')
    ('185', '65', '15', '88', 'T')
    >>> parse_pattern('225/40Z18 92W ')
    ('225', '40', '18', '92', 'W')
    """
    m = tyre_pattern_regex.search(pattern)
    if not m:
        return None

    width, ratio, rim, load_rating, speed_rating = m.groups()

    return width, ratio, rim, load_rating, speed_rating
