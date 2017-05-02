import os
import csv
import re
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))


def extract_data(pattern):
    """
    >>> extract_data('33X12.5 R15 108S')
    ('33', '12.5', '15', '108', 'S')
    >>> extract_data('215/65 R16 109/107R')
    ('215', '65', '16', '109/107', 'R')
    >>> extract_data('225/70 R15C 112R/110R')
    ('225', '70', '15', '112/110', 'R')
    >>> extract_data('215/50 R17 95W')
    ('215', '50', '17', '95', 'W')
    >>> extract_data('215/65 R16')
    ('215', '65', '16', '', '')
    >>> extract_data('215/65 R16C')
    ('215', '65', '16', '', '')
    >>> extract_data('31X10.5 R15 109S')
    ('31', '10.5', '15', '109', 'S')
    >>> extract_data('31X10.5 -15 109S')
    ('31', '10.5', '15', '109', 'S')
    >>> extract_data('215/60 -17 96H')
    ('215', '60', '17', '96', 'H')
    """
    m1 = re.search(r'([\w\.]*)[/|X]([\w\.]*) [a-z\-]+(\d*)[a-z]? ([\d]*[a-z]?/?[\d]*)([a-z]+)$', pattern, re.I)
    m2 = re.search(r'([\w\.]*)/([\w\.]*) [a-z\-]+(\d*)[a-z]?$', pattern, re.I)
    if m1:
        width, aspect_ratio, rim, load_rating, speed_rating = m1.groups()
        load_rating = load_rating.replace(speed_rating, '')
    elif m2:
        width, aspect_ratio, rim = m2.groups()
        speed_rating = load_rating = ''
    else:
        return None

    return width, aspect_ratio, rim, load_rating, speed_rating


class TyreleaderSpider(BaseSpider):
    name = 'tyreleader.co.uk_test'
    allowed_domains = ['tyreleader.co.uk']
    start_urls = ('http://www.tyreleader.co.uk',)
    tyre_sizes = []
    all_man_marks = {}
    custom_man_marks = {}

    #download_delay = 0.1

    def __init__(self, *args, **kwargs):
        super(TyreleaderSpider, self).__init__(*args, **kwargs)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.custom_man_marks['(*)'] = '*'

    def parse(self, response):
        self.log("Number of tyres: %s" % len(self.tyre_sizes))
        for i, row in enumerate(self.tyre_sizes, 1):
            key = "%s/%s/%s" % (row['Width'], row['Aspect Ratio'], row['Rim'])
            self.log("Searching for %d: %s" % (i, key))
            yield Request('http://www.tyreleader.co.uk/car-tyres-{}-{}-{}/'.format(row['Width'],
                                                                                   row['Aspect Ratio'],
                                                                                   row['Rim']),
                          callback=self.parse_search)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        urls = hxs.select('//div[@class="pagination pagination-centered"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin(base_url, url), callback=self.parse_search)
        #parse products list
        products = hxs.select('//*[@id="searchRes"]/tbody//tr')
        for product in products:
            season = product.select('.//td[4]/i/@class').extract()
            #skip winter tyres
            if season and 'ico-type ico-W' in season[0]:
                continue
            loader = ProductLoader(item=Product(), selector=product)
            brand, name = product.select('./td[2]/a/b/text()').extract()
            loader.add_value('name', name)

            pattern = product.select('./td[2]/a/small/text()').extract()[0]

            data = extract_data(pattern)
            if data:
                width, aspect_ratio, rim, load_rating, speed_rating = data
            else:
                self.log("ERROR. Unable to parse pattern: %s" % pattern)
                continue

            if 'goodrich' in brand.lower():
                brand = 'BFG'
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            price = product.select('.//span[@class="pr"]/text()').extract()[0]
            price_decimals = product.select('.//span[@class="pr"]/sup/text()').extract()[0].replace(u'\xa3', '')
            loader.add_value('price', extract_price(price + price_decimals))
            identifier = product.select('@data-id').extract()[0]
            loader.add_value('identifier', identifier)
            url = product.select('./td[2]/a/@href').extract()[0]
            loader.add_value('url', urljoin(base_url, url))
            image_url = product.select('./td[1]/img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin(base_url, image_url[0]))

            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = aspect_ratio
            metadata['rim'] = rim
            metadata['speed_rating'] = speed_rating
            metadata['width'] = width
            metadata['fitting_method'] = 'Delivered'
            metadata['load_rating'] = load_rating
            specif = product.select('.//span[@class="specif"]/text()').extract()
            specif = [x.lower() for x in specif]
            metadata['xl'] = 'Yes' if 'xl' in specif else 'No'
            metadata['run_flat'] = 'Yes' if 'runflat' in specif else 'No'

            man_code = ''
            for code, man_mark in self.all_man_marks.iteritems():
                if code.lower() in specif:
                    man_code = man_mark
                    break
            if man_code == '':
                for code, man_mark in self.custom_man_marks.iteritems():
                    if code.lower() in specif:
                        man_code = man_mark
                        break
            metadata['manufacturer_mark'] = man_code

            metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                   metadata['aspect_ratio'],
                                                   metadata['rim'],
                                                   load_rating,
                                                   speed_rating))
                                                   #metadata['alternative_speed_rating']))

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
