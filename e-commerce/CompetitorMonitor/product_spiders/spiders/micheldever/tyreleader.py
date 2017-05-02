import os
import csv
import json
import re
import pandas as pd
from urlparse import urljoin

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import DATA_DIR
from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand, is_run_flat


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
    name = 'tyreleader.co.uk'
    allowed_domains = ['tyreleader.co.uk']
    start_urls = ('https://www.tyreleader.co.uk',)
    tyre_sizes = []
    all_man_marks = {}
    custom_man_marks = {}

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
        self.old_meta_df = None

    def parse(self, response):
        if self.old_meta_df is None and hasattr(self, 'prev_crawl_id'):
            old_meta_filename = os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % self.prev_crawl_id)
            if os.path.exists(old_meta_filename):
                with open(old_meta_filename) as f:
                    self.old_meta_df = pd.DataFrame([json.loads(l.strip()) for l in f], dtype=pd.np.str)
        elif not hasattr(self, 'prev_crawl_id'):
            self.log('prev_crawl_id attr does not found')

        self.log("Number of tyres: %s" % len(self.tyre_sizes))
        for i, row in enumerate(self.tyre_sizes, 1):
            key = "%s/%s/%s" % (row['Width'], row['Aspect Ratio'], row['Rim'])
            self.log("Searching for %d: %s" % (i, key))
            yield Request('https://www.tyreleader.co.uk/car-tyres-{}-{}-{}/?orderby=prix'.format(row['Width'],
                                                                                                 row['Aspect Ratio'],
                                                                                                 row['Rim']),
                          callback=self.parse_search)

    def parse_search(self, response):
        base_url = get_base_url(response)

        urls = response.xpath('//div[@class="pagination tCenter"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin(base_url, url), callback=self.parse_search)

        products = response.xpath('//*[@class="table search-results vCenter"]/tbody//tr')
        for product in products:
            season = product.xpath('.//i[contains(@class, "season")]/@class').extract()

            if season and 'winter' in season[0]:
                continue
            loader = ProductLoader(item=Product(), selector=product)
            brand = product.xpath('./td/a[@class="item-ref"]/span[1]/text()').extract()[0]
            name = product.xpath('./td/a[@class="item-ref"]/span[2]/text()').extract()[0]
            loader.add_value('name', name)

            pattern = product.xpath('./td/a[@class="item-ref"]/small/text()').extract()[0]

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
            price = ''.join(product.xpath('.//div[@class="hidden-xs"]/span[@class="prix"]/text()').re(r'[\d\.,]+'))\
                      .replace('.', '').replace(",", ".")
            loader.add_value('price', extract_price(price))
            identifier = product.xpath('@data-id').extract()[0]
            loader.add_value('identifier', identifier)
            url = product.xpath('./td[2]/a/@href').extract()[0]
            loader.add_value('url', urljoin(base_url, url))
            image_url = product.xpath('./td[@class="img"]//img/@src').extract()
            if image_url:
                if len(image_url) < 250:
                    loader.add_value('image_url', urljoin(base_url, image_url[0]))

            if self.old_meta_df is not None:
                old_meta = self.old_meta_df[self.old_meta_df['identifier'] == identifier]
            else:
                old_meta = None

            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = aspect_ratio
            metadata['rim'] = rim
            metadata['speed_rating'] = speed_rating
            metadata['width'] = width
            metadata['fitting_method'] = 'Delivered'
            metadata['load_rating'] = load_rating
            specif = product.xpath('.//span[@class="specif"]/text()').extract()
            specif = [x.lower() for x in specif]
            metadata['xl'] = 'Yes' if 'xl' in specif else 'No'
            run_flat_found = is_run_flat('%s %s' % (name, ' '.join(specif)))
            metadata['run_flat'] = 'Yes' if ('runflat' in specif) \
                                            or ('run flat' in ' '.join(specif)) or run_flat_found else 'No'
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

            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                product_correct = False
                if (old_meta is not None) and (not old_meta.empty):
                    product['metadata'] = dict(old_meta.iloc[0].metadata)
                    try:
                        product_correct = is_product_correct(product)
                    except Exception, e:
                        self.log('%r' % e)
                        continue

                if not product_correct:
                    continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            yield product
