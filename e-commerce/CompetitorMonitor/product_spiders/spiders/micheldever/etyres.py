import os
import csv
import json
import re
from urlparse import urljoin

from scrapy import Spider, Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, \
    find_brand_segment, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))


class EtyresSpider(Spider):
    name = 'etyres.co.uk'
    allowed_domains = ['etyres.co.uk']
    start_urls = ('http://www.etyres.co.uk',)

    def __init__(self, *args, **kwargs):
        super(EtyresSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.matcher = Matcher(self.log)

        self.all_man_marks = {}
        self.custom_man_marks = {}
        self.tyre_sizes = []
        self.tyre_widths = {}
        self.tyre_profiles = {}
        self.tyre_rims = {}

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.ip_codes = {}
        self.ip_codes_filename = os.path.join(HERE, 'etyres_ip_codes.csv')
        if os.path.exists(self.ip_codes_filename):
            with open(self.ip_codes_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.ip_codes[row['identifier']] = row['ip_code']

        self.custom_man_marks[' JAGUAR FITMENT'] = 'J'
        self.custom_man_marks[' RAV4 FITMENT'] = ''
        self.custom_man_marks[' NISSAN JUKE FITMENT'] = ''
        self.custom_man_marks[' (PORSCHE FITMENT)'] = 'N0'
        self.custom_man_marks[' LEXUS FITMENT'] = ''
        self.custom_man_marks[' PRIUS FITMENT'] = ''
        self.custom_man_marks[' TOYOTA AURIS FITMENT'] = ''
        self.custom_man_marks[' - TOYOTA RAV4 FITMENT'] = ''
        self.custom_man_marks[' BMW MINI FITMENT'] = '*'
        self.custom_man_marks[' AUDI FITMENT'] = 'AO'
        self.custom_man_marks[' JAG FITMENT'] = 'J'
        self.custom_man_marks[' FERRARI MASERATI FITMENT'] = ''
        self.custom_man_marks[' MASERATI FITMENT'] = ''
        self.custom_man_marks[' - BMW FITMENT'] = '*'
        self.custom_man_marks[' ASTON MARTIN FITMENT'] = ''
        self.custom_man_marks[' MERCEDES & RENAULT FITMENT'] = 'MO'

    def spider_closed(self, spider):
        with open(self.ip_codes_filename, 'w') as f:
            writer = csv.DictWriter(f, ['identifier', 'ip_code'])
            writer.writeheader()
            for identifier, ip_code in self.ip_codes.iteritems():
                new_row = {'identifier': identifier, 'ip_code': ip_code}
                writer.writerow(new_row)

    def start_requests(self):
        yield Request('http://www.etyres.co.uk/js/getDropdown3.php', callback=self.parse_widths)

    def parse_widths(self, response):
        options = response.xpath('//option')
        for option in options:
            val = option.xpath('./@value').extract()
            if val:
                val = val[0]
                width = option.xpath('./text()').extract()[0]
                self.tyre_widths[width] = val
                yield Request('http://www.etyres.co.uk/js/getDropdown3.php?widthId={}&mode=1'.format(val),
                              meta={'width': val},
                              callback=self.parse_profiles)

    def parse_profiles(self, response):
        options = response.xpath('//option')
        width = response.meta.get('width')
        for option in options:
            val = option.xpath('./@value').extract()
            if val:
                val = val[0]
                profile = option.xpath('./text()').extract()[0]
                self.tyre_profiles[profile] = val
                yield Request('http://www.etyres.co.uk/js/getDropdown3.php?widthId={}&profileId={}&mode=2'.format(width, val),
                              callback=self.parse_rims)

    def parse_rims(self, response):
        options = response.xpath('//option')
        for option in options:
            val = option.xpath('./@value').extract()
            if val:
                val = val[0]
                rim = option.xpath('./text()').extract()[0]
                self.tyre_rims[rim] = val
                for x in self.search():
                    yield x

    def search(self):
        for row in self.tyre_sizes:
            if row['Width'] in self.tyre_widths and row['Aspect Ratio'] in self.tyre_profiles and row['Rim'] in self.tyre_rims:
                formdata = {'sort': 'cheap',
                            'manuf': 'all',
                            'mode': 'all',
                            'postcodeText': 'DH9 9DB',
                            'tyreWidthId': self.tyre_widths[row['Width']],
                            'tyreProfileId': self.tyre_profiles[row['Aspect Ratio']],
                            'tyreWheelId': self.tyre_rims[row['Rim']],
                            'tyreLoadRating': '0',
                            'tyreSpeedId': '0',
                            'orderBy': 'price',
                            'pcVar': '',
                            'vn': 'none',
                            'asc': '1',
                            'newmenu': 'YES',
                            'showmenu': 'YES',
                            'tyre4X4': 'F',
                            'searchSpeed': '13',
                            'corporateDiscount': '1',
                            'discountcode': 'none'}
                yield FormRequest('http://www.etyres.co.uk/fetchresults.php',
                                  formdata=formdata,
                                  meta={'row': row},
                                  callback=self.parse)

    def parse(self, response):
        base_url = get_base_url(response)
        row = response.meta['row']
        products = json.loads(response.body_as_unicode())
        for product_el in products:
            # skip winter tyres
            if product_el['winter'] != '0':
                continue
            loader = ProductLoader(item=Product(), selector=product_el)
            brand = product_el['tyreMake'].title()
            if 'goodrich' in brand.lower():
                brand = 'BFG'
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            load_rating = product_el['loadrating']
            speed_rating = product_el['tyreSpeed']
            loader.add_value('price', product_el['priceVat'])
            loader.add_value('identifier', product_el['id'])
            loader.add_value('url', urljoin('http://www.etyres.co.uk/tyre-detail/', product_el['URLString']))
            if product_el['tyreModelImage2']:
                image_url = 'images/' + product_el['tyreModelImage2']
                if image_url:
                    loader.add_value('image_url', urljoin(base_url, image_url))

            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = row['Aspect Ratio']
            metadata['rim'] = row['Rim']
            metadata['speed_rating'] = speed_rating
            metadata['width'] = row['Width']
            metadata['fitting_method'] = 'Fitted'
            metadata['load_rating'] = load_rating
            metadata['xl'] = 'Yes' if product_el['tyreReinforced'] == 'T' else 'No'
            run_flat_found = is_run_flat(product_el['tyreModel'])
            metadata['run_flat'] = 'Yes' if product_el['runflat'] == '1' or run_flat_found else 'No'

            name = product_el['tyreModel']
            man_code = ''
            for code, man_mark in self.all_man_marks.items():
                result, name = cut_name(code, name)
                if result:
                    man_code = man_mark
                    break
            if not man_code:
                for code, man_mark in self.custom_man_marks.items():
                    if name.endswith(code):
                        name = name.partition(code)[0]
                        man_code = man_mark
                        break
            metadata['manufacturer_mark'] = man_code

            metadata['full_tyre_size'] = '/'.join((row['Width'],
                                                   row['Aspect Ratio'],
                                                   row['Rim'],
                                                   load_rating,
                                                   speed_rating))
            name = name.replace(' EXTRA LOAD', '')
            name = name.replace(' RUNFLAT', '')

            loader.add_value('name', name.strip())

            metadata['fuel'] = product_el['rollingres']
            metadata['grip'] = product_el['wetgrip']
            metadata['noise'] = product_el['noisedb']

            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            if product['identifier'] in self.ip_codes:
                ip_code = self.ip_codes[product['identifier']]
                product['sku'] = ip_code
                product['metadata']['mts_stock_code'] = find_mts_stock_code(
                    product, spider_name=self.name, log=self.log,
                    ip_code=ip_code)
                yield product
            else:
                # We can't found IP code on products list, unfortunatelly we must extract it from product page
                yield Request(product['url'], meta={'product': product}, callback=self.parse_ipcode)

    def parse_ipcode(self, response):
        product = response.meta['product']
        ip_code = response.xpath('//form[@id="productForm"]//span[contains(@style, "color: #bbb")]/text()').re_first(r'IPC (.*)')
        self.ip_codes[product['identifier']] = ip_code or ''
        product['sku'] = ip_code
        product['metadata']['mts_stock_code'] = find_mts_stock_code(
            product, spider_name=self.name, log=self.log,
            ip_code=ip_code)
        yield product


def cut_name(w, text):
    if w == '*':
        for word in [' *', ' * ', '* ']:
            if word in text:
                text = text.partition(word)[0]
                return True, text
        return False, text
    match = re.compile(r'\b({0})\b'.format(re.escape(w)), flags=re.IGNORECASE).search(text)
    if match:
        text = text[:match.start()]
        return True, text
    else:
        return False, text
