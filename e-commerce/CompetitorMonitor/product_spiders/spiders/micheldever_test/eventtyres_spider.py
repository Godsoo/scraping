import re
import os
import csv
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, \
    get_speed_rating, get_alt_speed, find_brand_segment, unify_brand

from phantomjs import PhantomJS
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
import time


HERE = os.path.abspath(os.path.dirname(__file__))

brands_substitute = {
    'GT RADIAL': 'GT',
    'RUNWAY': 'ENDURO'
}

class EvenTyresSpider(BaseSpider):
    name = 'event-tyres.co.uk_test'
    allowed_domains = ['event-tyres.co.uk']
    #start_urls = ('http://www.event-tyres.co.uk/',)
    tyre_sizes = []
    all_man_marks = {}
    manually_matched = []

    def __init__(self, *args, **kwargs):
        super(EvenTyresSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                for i in range(1, 4):
                    new_row = row.copy()
                    new_row['specifictyre'] = str(i)
                    self.tyre_sizes.append(new_row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.errors = []

        '''
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        self._browser = PhantomJS(user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:25.0) Gecko/20100101 Firefox/25.0')
        self._browser.driver.set_page_load_timeout(300)
        self._browser.driver.set_script_timeout(300)

        self.log('>>> BROWSER: GET => http://www.event-tyres.co.uk/')
        self._browser.get('http://www.event-tyres.co.uk/')
        self.log('>>> BROWSER: OK')
        '''

    '''
    def spider_closed(self, spider):
        self._browser.close()
    '''

    def start_requests(self):
        for i, row in enumerate(self.tyre_sizes):
            yield Request('http://www.event-tyres.co.uk/', callback=self.next_search,
                          meta={'row': row, 'cookiejar': str(i)}, dont_filter=True)

    def next_search(self, response):
        hxs = HtmlXPathSelector(response)
        ntoken = hxs.select('//input[@name="ntoken"]/@value').extract()[0]
        row = response.meta['row']
        params = {'width': row['Width'],
                  'profile': row['Aspect Ratio'],
                  'size': row['Rim'], 'specifictyre': row['specifictyre'],
                  'postcode': 'WA5 7ZB', 'ntoken': ntoken}
        r = FormRequest(url='http://www.event-tyres.co.uk/tyre-search-results.php', meta={'cookiejar': response.meta['cookiejar']},
                        formdata=params)
        yield r


    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="result"]')

        for product_el in products:
            loader = ProductLoader(item=Product(), selector=product_el)

            brand = product_el.select('form/div/img[contains(@src, "brand")]/@alt').extract()[0]
            if brand in brands_substitute:
                brand = brands_substitute[brand]
            full_name = product_el.select('form/div/div/b/text()').extract()[0]
            try:
                tyre_size, name = re.split(brand, full_name, flags=re.I)
            except ValueError:
                self.log("[[TESTING]] Can not split tyre '%s' with brand '%s'" % (full_name, brand))
                continue
            # tyre_size, name = full_name.split(brand)
            loader.add_value('name', name)

            winter_tyre = product_el.select('form/div//img[@alt="Winter Tyre"]').extract()
            if not winter_tyre:
                loader.add_value('brand', unify_brand(brand))
                loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
                identifier = product_el.select('form/@id').extract()[0]

                out_of_stock = product_el.select('form/div//div[@class="availability"]')
                if out_of_stock:
                    loader.add_value('stock', 0)

                loader.add_value('url', get_base_url(response))

                image_url = product_el.select('form/div[@class="result_img"]/img[not(contains(@src, "brand"))]/@src').extract()

                if image_url:
                    loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))

                loader.add_value('identifier', identifier)
                price = product_el.select('form/div//div[contains(@id, "' + identifier + '|")]/text()').extract()[0]
                loader.add_value('price', price)

                metadata = MicheldeverMeta()
                res = parse_pattern(tyre_size)
                if not res:
                    # msg = "Error parsing %s" % tyre_size
                    # self.errors.append(msg)
                    # self.log(msg)
                    continue
                width, ratio, rim, load_rating, speed_rating = res
                # metadata['mts_stock_code'] = row['MTS Stock codee']
                metadata['aspect_ratio'] = ratio
                metadata['rim'] = rim
                metadata['speed_rating'] = speed_rating
                metadata['load_rating'] = load_rating
                metadata['width'] = width

                metadata['fitting_method'] = 'Fitted'
                metadata['alternative_speed_rating'] = ''
                xl = product_el.select('form/div/div/div/img[@alt="Extra Load Tyre"]').extract()
                metadata['xl'] = 'Yes' if xl else 'No'
                run_flat = product_el.select('form/div/div/div/img[@alt="Run Flat Tyre"]').extract()
                if not run_flat:
                    run_flat = ' RFT' in name
                metadata['run_flat'] = 'Yes' if run_flat else 'No'

                man_code = self._get_manufacturer_code(full_name)

                metadata['manufacturer_mark'] = man_code

                metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                       metadata['aspect_ratio'],
                                                       metadata['rim'],
                                                       metadata['load_rating'],
                                                       metadata['speed_rating']))
                                                       # metadata['alternative_speed_rating']))
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

        #yield Request('http://www.event-tyres.co.uk/', callback=self.next_search, dont_filter=True)

        '''
        for item in self.next_search(response):
            yield item
        '''

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
