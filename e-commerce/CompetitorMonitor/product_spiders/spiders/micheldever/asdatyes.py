# -*- coding: utf-8 -*-
import os.path
import csv
import re
import json
import urllib

from scrapy.spider import BaseSpider
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.selector import HtmlXPathSelector

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import fix_spaces

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand, is_run_flat

HERE = os.path.abspath(os.path.dirname(__file__))


class AsdaTyresSpider(BaseSpider):
    name = "asdatyres.co.uk"
    allowed_domains = ('asdatyres.co.uk',)

    all_man_marks = {}

    tyre_sizes = []
    search_requests = []

    download_timeout = 60

    def __init__(self, *args, **kwargs):
        super(AsdaTyresSpider, self).__init__(*args, **kwargs)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        self.errors = []

    def start_requests(self):
        seen_urls = set()
        cjar_no = 0
        for row in self.tyre_sizes:
            formdata = {
                'width': row['Width'],
                'profile': row['Aspect Ratio'],
                'diameter': row['Rim'],
                'speed': row['Speed rating']
            }

            self.log("Searching full tyre size: %s" % row['Full Tyre Size'])

            search_url = 'http://www.asdatyres.co.uk/%s-%s-%s?speed=%s' % (formdata['width'],
                                                                                    formdata['profile'],
                                                                                    formdata['diameter'],
                                                                                    formdata['speed'])

            if search_url not in seen_urls:
                self.search_requests.append(Request(search_url, callback=self.parse_search, dont_filter=True,
                                                    errback=self.errback,
                                                    meta={'search_row': row,
                                                          'cookiejar': cjar_no}))
                cjar_no += 1
                seen_urls.add(search_url)

            if row['Alt Speed']:
                formdata = {
                    'width': row['Width'],
                    'profile': row['Aspect Ratio'],
                    'diameter': row['Rim'],
                    'speed': row['Alt Speed']
                }

                self.log("Searching full tyre size: %s" % row['Full Tyre Size'])
                search_url = 'http://www.asdatyres.co.uk/%s-%s-%s?speed=%s' % (formdata['width'],
                                                                                        formdata['profile'],
                                                                                        formdata['diameter'],
                                                                                        formdata['speed'])
                if search_url not in seen_urls:
                    seen_urls.add(search_url)
                    self.search_requests.append(Request(search_url, callback=self.parse_search, dont_filter=True,
                                                        errback=self.errback,
                                                        meta={'search_row': row,
                                                              'cookiejar': cjar_no}))
                    cjar_no += 1

        self.search_requests.reverse()
        yield self.search_requests.pop()

    def errback(self, failure):
        if self.search_requests:
            yield self.search_requests.pop()

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)

        search_row = response.meta['search_row']

        self.log("Results for full tyre size: %s" % search_row['Full Tyre Size'])

        for p in self.extract_products(hxs, response.url):
            yield p

        total = hxs.select('//p[@class="total_tyres"]/text()').extract()[0].split()[0]
        total = int(total)
        max_page = total / 10 + 1 if total % 10 else 0
        meta = {'max_page': max_page, 'cookiejar': response.meta['cookiejar'],
                'search_row': response.meta['search_row']}

        if max_page >= 2:
            payload = {'order_by': 'price_asc', 'home_delivery_prices': '0'}
            yield Request('http://www.asdatyres.co.uk/update-tyres/2/', meta=meta, dont_filter=True,
                          callback=self.parse_page, method='POST', body=urllib.urlencode(payload),
                          errback=self.errback)
        elif self.search_requests:
            yield self.search_requests.pop()

    def parse_page(self, response):
        self.log('Parsing page')
        data = json.loads(response.body)['display_tyres']
        hxs = HtmlXPathSelector(text=data.encode('utf8'))

        for p in self.extract_products(hxs, response.url):
            yield p

        page = int(response.url.split('/')[-2]) + 1
        if page <= response.meta['max_page']:
            payload = {'order_by': 'price_asc', 'home_delivery_prices': '0'}
            yield Request('http://www.asdatyres.co.uk/update-tyres/%s/' % page, meta=response.meta,
                          callback=self.parse_page, dont_filter=True, method='POST', body=urllib.urlencode(payload),
                          errback=self.errback)
        elif self.search_requests:
            yield self.search_requests.pop()

    def extract_products(self, hxs, url):
        for el in hxs.select('//div[starts-with(@class,"tyre_container round")]'):
            tyre_options = fix_spaces("".join(el.select('.//p[@class="tyre_details"]//text()').extract())).strip()
            if not tyre_options:
                msg = 'Could not extract tyre options from element from %s' % url
                self.log('ERROR: %s' % msg)
                # self.errors.append(msg)
                continue
            res = parse_pattern(tyre_options)
            if not res:
                msg = "ERROR parsing: %s on %s" % (tyre_options, url)
                self.log(msg)
                # self.errors.append(msg)
                continue
            width, ratio, rim, load_rating, speed_rating, name = res

            # skip winter tyres
            if el.select(".//div[@class='tyre_winter']"):
                continue

            name = name.strip()
            identifier = el.select("./@id").extract()[0]
            price = "".join(el.select(".//p[@class='tyre_price']//text()").extract()).strip()
            if not price:
                continue
            brand = el.select(".//span[@class='tyre_brand_text']/text()").extract()[0]
            image_url = el.select('.//img[contains(@class, "tyre_image")]/@src').extract()[0]
            image_url = urljoin_rfc('http://asdatyres.co.uk', image_url)
            run_flat_found = is_run_flat(name)
            run_flat = 'Yes' if len(el.select(".//div[@class='tyre_rf']").extract()) > 0 or run_flat_found else 'No'
            xl = 'Yes' if len(el.select(".//div[@class='tyre_xl']").extract()) > 0 else 'No'

            if xl == 'Yes':
                name = name.replace("XL", "").strip()

            loader = ProductLoader(Product(), selector=hxs)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('price', price)
            loader.add_value('url', 'http://www.asdatyres.co.uk/')
            loader.add_value('image_url', image_url)
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))

            metadata = MicheldeverMeta()
            metadata['width'] = width
            metadata['aspect_ratio'] = ratio
            metadata['rim'] = rim
            metadata['load_rating'] = load_rating
            metadata['speed_rating'] = speed_rating
            metadata['fitting_method'] = 'Fitted'
            metadata['run_flat'] = run_flat
            metadata['xl'] = xl
            metadata['fitting_method'] = 'Fitted'

            man_code = ''
            for code, man_mark in self.all_man_marks.iteritems():
                if code in name:
                    man_code = man_mark
                    break
            metadata['manufacturer_mark'] = man_code

            metadata['full_tyre_size'] = '/'.join((width,
                                                   ratio,
                                                   rim,
                                                   load_rating,
                                                   speed_rating))

            fuel = el.select('.//div[@class="label_ratings"]/div[@class="fuel_rating"]//span[contains(@class, "label_rating_")]/text()').extract()
            grip = el.select('.//div[@class="label_ratings"]/div[@class="wet_rating"]//span[contains(@class, "label_rating_")]/text()').extract()
            noise = el.select('.//div[@class="label_ratings"]/div[contains(@class, "noise_rating")]/@data-decibels').extract()

            metadata['fuel'] = fuel[0] if fuel else ''
            metadata['grip'] = grip[0] if grip else ''
            metadata['noise'] = noise[0] if noise else ''

            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            yield product

tyre_pattern_regex = re.compile(r"(\d*)/(\d+\.?\d*)Z?R(\d*) \(?([\d/]*)([a-zA-Z]{1})\)? (.*)$")

def parse_pattern(pattern):
    """
    >>> parse_pattern('205/55R16 91V INF-040')
    ('205', '55', '16', '91', 'V', 'INF-040')
    >>> parse_pattern('255/35R19 (96Y) X Pilot Sport 3')
    ('255', '35', '19', '96', 'Y', 'X Pilot Sport 3')
    >>> parse_pattern('215/40ZR18 89W XL SN3970')
    ('215', '40', '18', '89', 'W', 'XL SN3970')
    """
    m = tyre_pattern_regex.search(pattern)
    if not m:
        return None

    width, ratio, rim, load_rating, speed_rating, name = m.groups()

    return width, ratio, rim, load_rating, speed_rating, name
