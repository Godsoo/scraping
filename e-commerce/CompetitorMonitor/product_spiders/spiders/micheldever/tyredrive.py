import re
import os
import csv
import urllib
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy import log

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))

class TyreDriveSpider(BaseSpider):
    name = 'micheldever-tyredrive.co.uk'
    allowed_domains = ['tyredrive.co.uk']
    start_urls = ('http://www.tyredrive.co.uk',)
    tyre_sizes = []
    all_man_marks = {}

    def __init__(self, *args, **kwargs):
        super(TyreDriveSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.errors = []

    def start_requests(self):
        for row in self.tyre_sizes:
            search = str(row['Width']) + '/' + str(row['Aspect Ratio']) + \
                     str(row['Speed rating']) + str(row['Rim'])
            parameters = {'section': row['Width'], 'profile': row['Aspect Ratio'], 'rim': row['Rim'], 'speed': '0', 'tyre_brand': '0', 'submit': 'SEARCH'}
            yield Request('http://www.tyredrive.co.uk/search.php?' + urllib.urlencode(parameters),
                              meta={'row': row, 'search': search}, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        row = response.meta['row']
        products = hxs.select('//td[@class="tyreinfo"]/a/@href').extract()
        log.msg('Products found: {!s} items [{}]'.format(len(products), response.url))
        if not products:
            log.msg('No products: [{}]'.format(response.url))

        pages = hxs.select('//a[contains(@href,"pagpage")]/@href').extract()
        for page in pages:
            yield Request(urljoin(base_url, page), meta=response.meta)

        for url in products:
            yield Request(urljoin(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        # the full name of the tyre (name variable) is used to extract metadata (i.e. run flat, xl),
        # the pattern should be set as the product's name
        name = hxs.select('//td[@class="tread"]/text()').extract()
        if not name:
            msg = "No name found on page: %s" % response.url
            # self.errors.append(msg)
            self.log("[ERROR] %s" % msg)
            return
        loader.add_value('name', name[0])
        brand = hxs.select('//table[@class="single searchresults"]//td[@class="tyreinfo"]/b/text()').extract()[0].strip()
        loader.add_value('brand', unify_brand(brand))
        loader.add_value('category', find_brand_segment(brand))
        fitting_method = 'Delivered'

        loader.add_value('url', response.url)

        out_of_stock = hxs.select('//table[@class="single searchresults"]//span[@class="outofstock"]')
        if out_of_stock:
            loader.add_value('stock', 0)

        image_url = hxs.select('//table[@class="single searchresults"]//td[@class="logo-pic"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))

        identifier = hxs.select('//table[@class="single searchresults"]//form/input[@name="pid"]/@value')[0].extract()
        loader.add_value('identifier', identifier)
        price = hxs.select('//table[@class="single searchresults"]//td[@class="netprice"]/text()')[0].extract()
        loader.add_value('price', price)

        name = hxs.select('//table[@class="single searchresults"]//td[@class="tyreinfo"]/span/text()')[0].extract()
        data = parse_pattern(name)
        if not data:
            log.msg('ERROR parsing "{}" [{}]'.format(name, response.url))
            # self.errors.append('ERROR parsing "{}" [{}]'.format(name, response.url))
            return
        metadata = MicheldeverMeta()
        metadata['aspect_ratio'] = data['Aspect_Ratio']
        metadata['rim'] = data['Rim']
        metadata['speed_rating'] = data['Speed_Rating']

        metadata['width'] = data['Width']
        metadata['fitting_method'] = fitting_method
        metadata['load_rating'] = data['Load_Rating']
        metadata['alternative_speed_rating'] = ''
        xl = 'XL' in name
        metadata['xl'] = 'Yes' if xl else 'No'

        run_flat_found = is_run_flat(loader.get_output_value('name') + ' ' + name)
        run_flat = 'rflat' in name.lower() or run_flat_found
        metadata['run_flat'] = 'Yes' if run_flat else 'No'
        if '*' in name:
            manufacturer_mark = '*'
        else:
            manufacturer_mark = [mark for mark in self.all_man_marks.keys() if mark in name.split(' ')]
        manufacturer_mark = manufacturer_mark[0].strip() if manufacturer_mark else []
        metadata['manufacturer_mark'] = self.all_man_marks.get(manufacturer_mark, '') if manufacturer_mark \
                                                                                      else ''
        metadata['mts_stock_code'] = ''
        metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                               metadata['aspect_ratio'],
                                               metadata['rim'],
                                               metadata['load_rating'],
                                               metadata['speed_rating']))
                                                # metadata['alternative_speed_rating']))

        fuel = hxs.select('//div[@class="eulabels"]/div/img/@src').re(r'fuel-(\w)')
        grip = hxs.select('//div[@class="eulabels"]/div/img/@src').re(r'grip-(\w)')
        noise = hxs.select('//div[@class="eulabels"]/div[contains(@class, "noise")]/strong/text()').extract()

        metadata['fuel'] = fuel[0].upper() if fuel else ''
        metadata['grip'] = grip[0].upper() if grip else ''
        metadata['noise'] = noise[0].upper() if noise else ''

        product = loader.load_item()
        product['metadata'] = metadata

        if not is_product_correct(product):
            return

        product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

        yield product

    def match_name(self, search_name, new_item, match_threshold=80, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold


def parse_pattern(pattern):
    """
    >>> parse_pattern('215/55 R16 TOYO PXCF2 93V') == {'Width': '215', 'Aspect_Ratio': '55', 'Rim': '16', 'Load_Rating': '93', 'Speed_Rating': 'V'}
    True
    >>> parse_pattern('215/55 ZR16 TOYO PXCF2 93V') == {'Width': '215', 'Aspect_Ratio': '55', 'Rim': '16', 'Load_Rating': '93', 'Speed_Rating': 'V'}
    True
    """
    data = re.search('(?P<Width>\d+)/(?P<Aspect_Ratio>\d+\.?\d*) {0,4}Z?R ?(?P<Rim>\d+) .* ?(?P<Load_Rating>\d{2,}/?\d*)(?P<Speed_Rating>[A-Z]{1,2})',
                     pattern)
    if data:
        return data.groupdict()
    else:
        return None
