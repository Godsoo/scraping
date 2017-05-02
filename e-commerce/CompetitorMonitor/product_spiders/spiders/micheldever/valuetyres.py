import re
import os
import csv

from scrapy import Spider, Request, FormRequest
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, \
    find_brand_segment, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))

MANUFACTURER_MARKS = {'K1': 'K1',
                      'K2': 'K1',
                      'C1': 'C1',
                      'N0': 'NO',
                      'N1': 'NO',
                      'N2': 'NO',
                      'N3': 'NO',
                      'N4': 'NO',
                      'N5': 'NO',
                      'N6': 'NO',
                      '*': '*',
                      'RO1': 'R01',
                      'R02': 'R01',
                      'M0': 'M0',
                      'MO': 'M0',
                      'M02': 'M0',
                      'AO': 'A0',
                      'EZ': 'A0',
                      'VO': 'V0',
                      'A': 'A',
                      'ST': 'ST',
                      'B': 'B',
                      'B1': 'B',
                      'J': 'J'}


class ValueTyresSpider(Spider):
    name = 'valuetyres.co.uk'
    allowed_domains = ('valuetyres.co.uk',)
    start_urls = ('http://www.valuetyres.co.uk/',)

    tyre_sizes = []
    all_man_marks = {}
    custom_man_marks = {}

    def _get_manufacturer_code(self, name):
        name = name.upper()
        for code, manufacturer_mark in self.all_man_marks.items():
            if code not in name:
                continue

            if code in name.split(' ') or code == '*':
                return manufacturer_mark

        return ''

    def __init__(self, *args, **kwargs):
        super(ValueTyresSpider, self).__init__(*args, **kwargs)
        self.current_tyre = 0
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        self.ip_codes = {}
        self.ip_codes_filename = os.path.join(HERE, 'vtyres_ip_codes.csv')
        if os.path.exists(self.ip_codes_filename):
            with open(self.ip_codes_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.ip_codes[row['identifier']] = row['ip_code']

        self.errors = []

        self.search_history = set()
        self.urls_history = set()

    def _get_history_key(self, search_params):
        key = "%(width)s-%(rim)s-%(aspect_ratio)s-%(speed_rating)s" % search_params
        return key

    def check_in_history(self, search_params):
        if self._get_history_key(search_params) in self.search_history:
            return True
        return False

    def add_to_history(self, search_params):
        self.search_history.add(self._get_history_key(search_params))

    def spider_idle(self, *args, **kwargs):
        self.urls_history = set()
        self.current_tyre += 1
        if self.current_tyre < len(self.tyre_sizes):
            req = Request(self.start_urls[0],
                          dont_filter=True,
                          callback=self.parse,
                          meta={'cookiejar': self.current_tyre})
            self.crawler.engine.crawl(req, self)

    def spider_closed(self, spider):
        with open(self.ip_codes_filename, 'w') as f:
            writer = csv.DictWriter(f, ['identifier', 'ip_code'])
            writer.writeheader()
            for identifier, ip_code in self.ip_codes.iteritems():
                new_row = {'identifier': identifier, 'ip_code': ip_code}
                writer.writerow(new_row)

    def get_next_tyre_search_request(self, response):
        r = None
        if self.current_tyre < len(self.tyre_sizes):
            row = self.tyre_sizes[self.current_tyre]
            for speed_rating in [row['Speed rating'], row['Alt Speed']]:
                if not speed_rating:
                    continue

                search_params = {
                    'width': row['Width'],
                    'aspect_ratio': row['Aspect Ratio'],
                    'speed_rating': speed_rating,
                    'rim': row['Rim']
                }

                self.log('>> Current search => %r:' % search_params)

                if self.check_in_history(search_params):
                    continue

                self.add_to_history(search_params)

                formdata = {
                    'ctl00$ctl00$InnerPH$ddl_tyre_width': search_params['width'],
                    'ctl00$ctl00$InnerPH$ddl_tyre_profile': search_params['aspect_ratio'],
                    'ctl00$ctl00$InnerPH$ddl_wheel_dia': search_params['rim'],
                    'ctl00$ctl00$InnerPH$ddl_speed_rating': search_params['speed_rating'],
                    'ctl00$ctl00$InnerPH$InnerPH$ddlwidth': search_params['width'],
                    'ctl00$ctl00$InnerPH$InnerPH$ddlprofile': search_params['aspect_ratio'],
                    'ctl00$ctl00$InnerPH$InnerPH$ddldia': search_params['rim'],
                    'ctl00$ctl00$InnerPH$InnerPH$ddlspeed': search_params['speed_rating']
                }

                r = FormRequest.from_response(response, formname='search_form',
                                              formdata=formdata,
                                              meta={
                                                  'cookiejar': self.current_tyre,
                                                  'speed_rating': speed_rating,
                                                  'search_params': search_params,
                                                  'proxy_service_disabled': True,
                                                  'proxy': response.meta.get('proxy', ''),
                                              },
                                              callback=self.parse_products,
                                              dont_filter=True)
        return r

    def parse(self, response):
        yield self.get_next_tyre_search_request(response)

    def parse_products(self, response):
        meta = {
            'cookiejar': response.meta['cookiejar'],
            'speed_rating': response.meta['speed_rating'],
            'search_params': response.meta['search_params'],
            'proxy_service_disabled': True,
            'proxy': response.meta.get('proxy', ''),
        }
        see_more_links = response.xpath('//*[@id="InnerPH_InnerPH_search_table_footer"]'
                                        '//a[contains(@class, "seeMore-")]/@href')\
                                 .extract()
        for url in see_more_links:
            yield Request(response.urljoin(url),
                          meta=meta,
                          callback=self.parse_products_data,
                          dont_filter=True)

    def parse_products_data(self, response):
        meta = {
            'cookiejar': response.meta['cookiejar'],
            'speed_rating': response.meta['speed_rating'],
            'search_params': response.meta['search_params'],
            'proxy_service_disabled': True,
            'proxy': response.meta.get('proxy', ''),
        }

        # Pages
        for url in response.xpath('//*[@id="InnerPH_InnerPH_pageList"]//a/@href').extract():
            url = response.urljoin(url)
            if url not in self.urls_history:
                self.urls_history.add(url)
                yield Request(url,
                              meta=meta,
                              callback=self.parse_products_data,
                              dont_filter=True)

        products = response.xpath('//ul[@id="results_tbl"]/li')
        if not products:
            products = response.xpath('//div[@class="product_item"]')
        if not products:
            self.log('No products found => %r' % response.meta)
        brand_list = response.xpath('//ul[@id="InnerPH_InnerPH_brand_list"]//a/text()').extract()
        if not brand_list:
            self.log('No brand list found => %r' % response.meta)
            return
        for product in products:
            desc = product.xpath('.//div[@class="tyre_desc"]/text()').extract()[0]
            if 'snow' in desc or 'winter' in desc:
                continue

            search_params=response.meta['search_params']

            name = product.xpath('.//a[@class="tyre_name"]/text()').extract()[0]
            url = product.xpath('.//a[@class="tyre_name"]/@href').extract()[0]
            p_id = product.xpath('.//a[@class="tyre_name"]/@href').re(r'/t(\d+)/')[0]
            image_url = product.xpath('.//*[contains(@class, "tyre_img")]//img/@src').extract()[0]
            try:
                brand = filter(lambda b: b in name, brand_list)[0]
            except:
                self.log('Can\'t detect brand for: %s' % name)
                continue
            try:
                price = product.xpath('.//*[@class="tyre_price_text"]/text()').extract()[0]
            except IndexError:
                self.log("Price not found: %s" % str(product))
                continue

            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('url', response.urljoin(url))
            loader.add_value('identifier', p_id)
            loader.add_value('image_url', image_url)
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            loader.add_value('price', price)

            pattern = name.strip()
            pattern = pattern.upper()
            pattern = pattern.replace('XL', '').replace('RFT', '').replace('RFLAT', '').replace('RUNFLAT', '').strip()

            loader.add_value('name', pattern)

            m = MicheldeverMeta()
            m['aspect_ratio'] = search_params['aspect_ratio']
            m['rim'] = search_params['rim']
            m['width'] = search_params['width']
            m['speed_rating'] = search_params['speed_rating'].upper()
            res = re.search('([\d/]+)%s' % search_params['speed_rating'].upper(), desc)
            if res:
                m['load_rating'] = res.groups()[0]
            else:
                self.log('ERROR: not load rating: %s' % url)
                m['load_rating'] = ''
            run_flat_found = is_run_flat(desc)
            if 'ZPS' in desc.upper() or 'RFT' in desc.upper() or 'RFLAT' in desc.upper() or \
               'RUNFLAT' in desc.upper() or 'RUN FLAT' in desc.upper() or run_flat_found:
                    m['run_flat'] = 'Yes'
            else:
                m['run_flat'] = 'No'

            if 'XL' in desc.upper():
                m['xl'] = 'Yes'
            else:
                m['xl'] = 'No'

            m['full_tyre_size'] = '/'.join((m['width'],
                                            m['aspect_ratio'],
                                            m['rim'],
                                            m['load_rating'],
                                            m['speed_rating']))

            m['fitting_method'] = 'Fitted' if'FITTED' in product.xpath('.//*[@class="tyre_price_type"]/text()').extract() else 'Delivered'
            m['manufacturer_mark'] = self._get_manufacturer_code(desc)

            fuel = product.xpath('.//*[@class="fuel-img"]/@data-grade').extract()
            m['fuel'] = fuel[0] if fuel else ''
            grip = product.xpath('.//*[@class="wetgrip-img"]/@data-grade').extract()
            m['grip'] = grip[0] if grip else ''
            noise = product.xpath('.//*[@class="noise-img"]/@data-grade').extract()
            m['noise'] = noise[0] if noise else ''

            product = loader.load_item()
            product['metadata'] = m

            if not is_product_correct(product):
                self.log('Product is not correct => %s' % desc)
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

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
        ip_code = ''
        product = response.meta['product']
        stock_number = response.xpath('//p[@id="InnerPH_InnerPH_spec_detail"]//text()').re_first(r'Stock Number: (.*)')
        width, ratio, rim, load, speed = product['metadata']['full_tyre_size'].split('/')
        size_speed = width + ratio + rim + speed
        if size_speed in stock_number:
            # ie: 2055516VBR7101
            # 2055516V + BR + 7101
            # Size + speed: 2055516V (width + ratio + rim + speed)
            # Manufacturer: BR (Two characters ID)
            # IP code: 7101
            ip_code = stock_number.split(width + ratio + rim + speed)[-1][2:]
        self.ip_codes[product['identifier']] = ip_code
        product['sku'] = ip_code
        product['metadata']['mts_stock_code'] = find_mts_stock_code(
            product, spider_name=self.name, log=self.log,
            ip_code=ip_code)
        yield product
