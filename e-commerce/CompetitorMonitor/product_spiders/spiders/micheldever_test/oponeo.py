import re
import os
import csv
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher

from scrapy import log

from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand

HERE = os.path.abspath(os.path.dirname(__file__))


class OponeoSpider(BaseSpider):
    name = 'oponeo.co.uk_test'
    allowed_domains = ['oponeo.co.uk']
    start_urls = ('http://www.oponeo.co.uk',)
    tyre_sizes = []
    all_man_marks = {}

    download_delay = 1

    def __init__(self, *args, **kwargs):
        super(OponeoSpider, self).__init__(*args, **kwargs)

        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.errors = []

    def start_requests(self):
        requests = []
        cookie = 1
        self.log("[OPONEO] Row to process: %d" % len(self.tyre_sizes))

        for i, row in enumerate(self.tyre_sizes, 1):
            self.log("[OPONEO] Searching for tyre %d: %s, MTS code: %s" % (i, row['Full Tyre Size'], row['MTS Stockcode']))
            search = str(row['Width']) + '/' + str(row['Aspect Ratio']) + \
                     str(row['Speed rating']) + str(row['Rim'])
            meta = {'row': row, 'search': search, 'cookiejar': cookie}
            cookie += 1
            search_url = 'http://www.oponeo.co.uk/tyre-finder/s=2/summer,all-season/t=1/car/r=1/{Width}-{Aspect Ratio}-r{Rim}'.format(**row)
            yield Request(search_url, meta=meta,
                          headers={'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0'})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//*[@id="productList"]//div[@itemprop="offers"]')

        next_page = hxs.select('//li[contains(@class, "next") and contains(@class, "nextItem")]/a/@id').extract()
        if next_page:
            next_page_id = next_page[0]
            req = FormRequest.from_response(response, formname='form1',
                formdata={'__ASYNCPOST': 'true', '__EVENTTARGET': next_page_id, '__EVENTARGUMENT': ''},
                headers={'X-MicrosoftAjax': 'Delta=true', 'X-Requested-With': 'XMLHttpRequest',
                         'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:30.0) Gecko/20100101 Firefox/30.0'},
                meta=response.meta,
                callback=self.parse_next_page,
                dont_filter=True)
            yield req


        for product in products:
            product_url = product.select('.//div[@class="productName"]//a/@href')[0].extract()
            yield Request(urljoin(base_url, product_url), callback=self.parse_product, meta=response.meta)

    def parse_next_page(self, response):
        yield Request(response.url, dont_filter=True, meta=response.meta)

    def retry_request(self, response):
        try_no = response.meta.get('try', 1)
        if try_no < self.max_retry_count:
            meta = {
                'try': try_no + 1
            }
            meta['recache'] = True
            self.log("[WARNING] Retrying. Failed to scrape product page: %s" % response.url)
            yield Request(response.url,
                          meta=meta,
                          callback=self.parse_product,
                          dont_filter=True)
        else:
            self.log("[WARNING] Gave up. Failed to scrape product page: %s" % response.url)
            self.errors.append("Failed to scrape product page: %s" % response.url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        # the full name of the tyre (name variable) is used to extract metadata (i.e. run flat, xl),
        # the pattern should be set as the product's name

        fitting_method = 'Delivered'

        loader.add_value('url', response.url)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))

        identifier = hxs.select('//form[@name="form1"]/@action').extract()
        if not identifier:
            yield self.retry_request(response)
            return
        identifier = identifier[0]
        loader.add_value('identifier', identifier)
        price = hxs.select('//*[@class="price"]/*[@class="mainPrice"]/text()')[0].extract()
        loader.add_value('price', price)
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)

        brand = hxs.select('//div[@class="hidden"]/input[@class="producerName"]/@value').extract()
        if not brand:
            yield self.retry_request(response)
            return
        brand = brand[0].strip()
        loader.add_value('brand', unify_brand(brand))
        loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
        brand = re.sub(u'\u0119', u'e', brand)

        product_name = hxs.select('//h1[@itemprop="name"]/text()')[0].extract().strip()
        product_name = re.sub(u'[:\u2122]', u'', product_name)
        product_name = product_name.replace(brand, '').strip()

        data = parse_pattern(product_name)
        if not data:
            log.msg('ERROR parsing "{}" [{}]'.format(product_name, response.url))
            self.errors.append('ERROR parsing "{}" [{}]'.format(product_name, response.url))
            return

        loader.add_value('name', data['Name'])

        metadata = MicheldeverMeta()
        metadata['aspect_ratio'] = data['Aspect_Ratio']
        metadata['rim'] = data['Rim']
        metadata['speed_rating'] = data['Speed_Rating']

        metadata['width'] = data['Width']
        metadata['fitting_method'] = fitting_method
        metadata['load_rating'] = data['Load_Rating'] or ''
        metadata['alternative_speed_rating'] = ''
        xl = 'XL' in product_name
        metadata['xl'] = 'Yes' if xl else 'No'

        run_flat = 'run on flat' in product_name.lower() or 'run flat' in product_name.lower()
        metadata['run_flat'] = 'Yes' if run_flat else 'No'
        manufacturer_mark = [mark for mark in self.all_man_marks.keys() if mark in product_name.split(' ')]
        manufacturer_mark = manufacturer_mark[0].strip() if manufacturer_mark else []
        metadata['manufacturer_mark'] = self.all_man_marks.get(manufacturer_mark, '') if manufacturer_mark else ''
        metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                               metadata['aspect_ratio'],
                                               metadata['rim'],
                                               metadata['load_rating'],
                                               metadata['speed_rating']))
                                                # metadata['alternative_speed_rating']))

        product = loader.load_item()
        product['metadata'] = metadata

        if not is_product_correct(product):
            return

        product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

        new_speed_rating = get_speed_rating(product)
        new_alt_speed = get_alt_speed(product)
        product['metadata']['alternative_speed_rating'] = new_alt_speed if new_alt_speed else \
            product['metadata']['speed_rating'] if product['metadata']['speed_rating'] != new_speed_rating else ''
        product['metadata']['speed_rating'] = new_speed_rating

        yield product

    def match_name(self, search_name, new_item, match_threshold=80, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold


def parse_pattern(pattern):
    """
    >>> parse_pattern('ASD 215/55 R16 93 V') == {'Name': 'ASD', 'Width': '215', 'Aspect_Ratio': '55', 'Rim': '16', 'Load_Rating': '93', 'Speed_Rating': 'V'}
    True
    >>> parse_pattern('QWE 205/65 R16 107/105 R') == {'Name': 'QWE', 'Width': '205', 'Aspect_Ratio': '65', 'Rim': '16', 'Load_Rating': '107/105', 'Speed_Rating': 'R'}
    True
    >>> parse_pattern('TR 928 205/55 R16 91 V') == {'Name': 'TR 928', 'Width': '205', 'Aspect_Ratio': '55', 'Rim': '16', 'Load_Rating': '91', 'Speed_Rating': 'V'}
    True
    """
    data = re.search('(?P<Name>.*) (?P<Width>\d+)/(?P<Aspect_Ratio>\d+\.?\d*) R(?P<Rim>\d+) (?P<Load_Rating>\d+/?\d*)? (?P<Speed_Rating>[A-Z]{1,2})',
                     pattern)
    if data:
        return data.groupdict()
    else:
        return None
