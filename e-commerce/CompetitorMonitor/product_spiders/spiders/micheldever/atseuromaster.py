"""
Account: Micheldever
Name: shop.atseuromaster.co.uk
Ticket URL: https://www.assembla.com/spaces/competitormonitor/tickets/4886

IMPORTANT!!

This site is tricky and sometimes it does not show the tag for the Run Flat Tyres,
so we need to do a search by filtering by run flat first to extract the Run Flat Tyres first and then
collect all the rest of the tyres.
Also if the search returns only one tyre the website redirects to the page of this product.
"""

import os
import csv
import re
from scrapy import Spider, FormRequest
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from micheldeveritems import MicheldeverMeta
from micheldeverutils import (
    find_manually_matched_mts_stock_code,
    is_product_correct,
    find_brand_segment,
    unify_brand,
)


HERE = os.path.abspath(os.path.dirname(__file__))


class ATSEuromasterSpider(Spider):
    name = 'shop.atseuromaster.co.uk'
    allowed_domains = ['shop.atseuromaster.co.uk']
    start_urls = ['https://shop.atseuromaster.co.uk/']

    def __init__(self, *args, **kwargs):
        super(ATSEuromasterSpider, self).__init__(*args, **kwargs)

        self.tyre_sizes = []
        self.all_man_marks = {}
        self.custom_man_marks = {}

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

    def parse(self, response):
        for i, row in enumerate(self.tyre_sizes, 1):
            key = "%s/%s/%s" % (row['Width'], row['Aspect Ratio'], row['Rim'])
            self.log("Searching for %d: %s" % (i, key))
            run_flat_url = 'https://shop.atseuromaster.co.uk/search_tyres/tyres-%(Width)s-%(Aspect Ratio)s-%(Rim)s-0-0--run-flat' % row
            all_url = 'https://shop.atseuromaster.co.uk/search_tyres/tyres-%(Width)s-%(Aspect Ratio)s-%(Rim)s-0-0' % row
            yield FormRequest(run_flat_url,
                              formdata={'loadCriteriaFromSession': 'false',
                                        'order': 'PRICE',
                                        'searchByRF': 'false',
                                        'searchByXL': 'false',
                                        'season': '',
                                        'selectedAspectRatioValue': row['Aspect Ratio'],
                                        'selectedLoadIndexValue': '',
                                        'selectedRimDiameterValue': row['Rim'],
                                        'selectedSectionValue': row['Width'],
                                        'selectedSpeedIndexValue': ''},
                              meta={'next_url': all_url,
                                    'row': row.copy()},
                              callback=self.parse_search,
                              dont_filter=True)

    def parse_search(self, response):
        # Next URL found?
        if 'next_url' in response.meta:
            row = response.meta['row']
            yield FormRequest(response.meta['next_url'],
                              formdata={'loadCriteriaFromSession': 'false',
                                        'order': 'PRICE',
                                        'searchByRF': 'false',
                                        'searchByXL': 'false',
                                        'season': '',
                                        'selectedAspectRatioValue': row['Aspect Ratio'],
                                        'selectedLoadIndexValue': '',
                                        'selectedRimDiameterValue': row['Rim'],
                                        'selectedSectionValue': row['Width'],
                                        'selectedSpeedIndexValue': ''},
                              callback=self.parse_search,
                              dont_filter=True)

        # Parse results
        results = response.xpath('//div[@id="tyresrch-res"]/div')
        for result_xs in results:
            is_winter = bool(result_xs.xpath('.//*[@alt="WINTER"]').extract())
            if is_winter:
                continue

            try:
                brand = result_xs.xpath('.//span[@class="nom-marque"]/text()').extract()[0]
            except:
                brand = ''
            try:
                name = result_xs.xpath('.//span[@class="title"]/strong/text()').extract()[0]
            except:
                name = ''

            try:
                size = result_xs.xpath('normalize-space(.//span[@class="size"]/text())').extract()[0]
                if len(results) > 1:
                    width, aspect_ratio, rim, load_rating, speed_rating = re.search(r'(\d+)/(\d+)\sR(\d+)\s(\d+)(.)', size).groups()
                else:
                    try:
                        width, aspect_ratio, _, rim, load_rating, speed_rating = re.findall(r'[\d\w]+', size)
                    except:
                        width, aspect_ratio, rim, load_rating, speed_rating = re.search(r'(\d+)/(\d+)\sR(\d+)\s(\d+)(.)', size).groups()
            except:
                self.log("ERROR - Unable to parse pattern for name %s in %s" % (name, response.url))
                continue

            is_run_flat = bool(result_xs.xpath('.//*[contains(text(), "Run Flat")]').extract())
            is_xl = bool(result_xs.xpath('.//*[contains(text(), "Extraload")]').extract())

            product_id = result_xs.xpath('.//input[@name="chkCompare"]/@value').extract()
            if not product_id:
                product_id = result_xs.re(r'productDetail/id/(.*?)/mode')
            if not product_id:
                continue

            price = result_xs.xpath('.//span[@class="price"]/text()').extract()
            if not price:
                price = result_xs.xpath('.//*[@itemprop="price"]/text()').extract()

            product_url = map(response.urljoin, result_xs.xpath('.//a[@class="moreinfo"]/@href').extract())
            product_img = map(response.urljoin, result_xs.xpath('.//div[@class="tyre-image"]/img[1]/@src').extract())

            try:
                fuel, grip, noise = result_xs.xpath('.//div[@class="tyre-labelling-content"]//span[contains(@class, '
                                                    '"tyre-labelling-letter-")]/text()').re(r'[\w\d]+')
            except:
                fuel = ''
                grip = ''
                noise = ''

            loader = ProductLoader(item=Product(), selector=result_xs)
            loader.add_value('identifier', product_id[0])
            loader.add_value('name', name)
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            loader.add_value('price', extract_price(price[0]))
            if product_url:
                loader.add_value('url', product_url[0])
            else:
                loader.add_value('url', response.url)
            if product_img:
                loader.add_value('image_url', product_img[0])

            product = loader.load_item()

            try:
                manuf = result_xs.xpath('.//div[@class="info"]//text()').extract()[3].strip().lower()
            except:
                manuf = ''

            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = aspect_ratio
            metadata['rim'] = rim
            metadata['speed_rating'] = speed_rating
            metadata['width'] = width
            metadata['fitting_method'] = 'Fitted'
            metadata['load_rating'] = load_rating
            metadata['xl'] = 'Yes' if is_xl else 'No'
            metadata['run_flat'] = 'Yes' if is_run_flat else 'No'

            man_code = ''
            for code, man_mark in self.all_man_marks.iteritems():
                if code.lower() in manuf:
                    man_code = man_mark
                    break

            metadata['manufacturer_mark'] = man_code
            metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                   metadata['aspect_ratio'],
                                                   metadata['rim'],
                                                   load_rating,
                                                   speed_rating))
            metadata['fuel'] = fuel
            metadata['grip'] = grip
            metadata['noise'] = noise
            product['metadata'] = metadata
            if not is_product_correct(product):
                self.log('The product is not correct => %r' % product)
                continue

            # Only manual MTS Stock codes for now
            mts_stock_code = find_manually_matched_mts_stock_code(product, spider_name=self.name)
            if mts_stock_code:
                self.log('MTS Manually matched: %s' % mts_stock_code)
            product['metadata']['mts_stock_code'] = mts_stock_code

            yield product
