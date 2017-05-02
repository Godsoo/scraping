# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os.path
import csv
import re

from scrapy.spider import BaseSpider
from scrapy.http import FormRequest, Request
from scrapy.selector import HtmlXPathSelector
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider

from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand, fix_spaces

HERE = os.path.abspath(os.path.dirname(__file__))

man_mark_mapping = {
    u'audi.png': 'AO',
    u'mercedes.png': 'MO',
    u'volkswagen.png': '',
    u'bmw.png': '*'
}

brand_img_mapping = {
}


class CarTyresSpider(BaseSpider):
    name = "cartyres.com_test"
    domain = "cartyres.com"

    start_urls = ['http://cartyres.com', ]

    all_man_marks = {}

    tyre_sizes = []
    search_requests = []

    max_retry_count = 5

    def __init__(self, *args, **kwargs):
        super(CarTyresSpider, self).__init__(*args, **kwargs)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.errors = []

        self.row_generator = self.row_generator_func()
        self.makes = []
        self.processed_rows = {}

        self.current_row = None
        self.current_row_processed_makes = set()

        self.current_make_prods = set()
        self.prev_make_prods = set()

        self.man_marks = set()

        self.done = False

        self.errors = []

    def spider_idle(self, spider):
        self.log("[CARTYRES] Spider idle")
        if not self.done:
            if self.current_row:
                self.log("[CARTYRES] Continuing current row")
            else:
                self.log("[CARTYRES] Continuing next row")
            request = Request(self.start_urls[0], dont_filter=True, callback=self.parse)
            self._crawler.engine.crawl(request, self)
            raise DontCloseSpider()
        else:
            self.log("[CARTYRES] Man marks found: %s" % self.man_marks)
            for man_mark in self.man_marks:
                if not man_mark in man_mark_mapping:
                    self.log('[CARTYRES] Man mark not in mapping: %s' % man_mark)

    def get_row_key(self, row):
        fields_to_save = ['Width', 'Rim', 'Aspect Ratio', 'Speed rating']
        return tuple([row[x] for x in fields_to_save])

    def check_row_is_processed(self, row):
        key = self.get_row_key(row)
        if self.processed_rows.get(key):
            return True
        return False

    def add_row_to_history(self, row):
        key = self.get_row_key(row)
        self.processed_rows[key] = True

    def row_generator_func(self):
        for i, row in enumerate(self.tyre_sizes):
            if row['Speed rating'] and row['Alt Speed']:
                res = row.copy()
                if not self.check_row_is_processed(res):
                    self.add_row_to_history(res)
                    yield res
                res = row.copy()
                res['Speed rating'] = res['Alt Speed']
                if not self.check_row_is_processed(res):
                    self.add_row_to_history(res)
                    yield res
            else:
                res = row.copy()
                if not self.check_row_is_processed(res):
                    self.add_row_to_history(res)
                    yield res

    def get_next_row(self):
        try:
            row = next(self.row_generator)
        except StopIteration:
            return None
        self.current_row = row
        self.current_row_processed_makes = set()
        return row

    def prepare_for_next_row(self):
        self.current_row = None
        self.current_row_processed_makes = set()
        self.current_make_prods = set()
        self.prev_make_prods = set()

    def prepare_for_next_make(self):
        self.current_make_prods = set()
        self.prev_make_prods = self.current_make_prods

    def get_post_data(self, response):
        def async_get_value(data, key, default=""):
            if key in data:
                index = data.index(key)
                if len(data) > index:
                    return data[index + 1]
            return default

        hxs = HtmlXPathSelector(response)
        data = {}
        res_data = response.body.split("|")
        data['__VIEWSTATE'] = async_get_value(res_data, '__VIEWSTATE')
        data['__EVENTVALIDATION'] = async_get_value(res_data, '__EVENTVALIDATION')
        data['__VIEWSTATEGENERATOR'] = async_get_value(res_data, '__VIEWSTATEGENERATOR')

        for el in hxs.select(".//select"):
            key = el.select("@name").extract()
            value = el.select(".//option[@selected]/@value").extract()
            if key:
                key = key[0]
                if value:
                    value = value[0]
                else:
                    value = ''
                data[key] = value

        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ValidCar'] = 'rbYes'
        data['__EVENTARGUMENT'] = ""
        data['__LASTFOCUS'] = ""
        data['__ASYNCPOST'] = 'true'

        if not data.get('ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlSpeedL', ""):
            data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlSpeedL'] = 'All'

        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvDiameter'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvProfile'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvSpeed'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvWidth'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtPostCodeL'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtPostCodeR'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtRegNo'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtValidRegNo'] = ""
        return data

    def parse(self, response):
        row = self.current_row
        if not row:
            row = self.get_next_row()
        if not row:
            self.done = True
            return
        self.log("[CARTYRES] Searching row: %s" % str(row))

        hxs = HtmlXPathSelector(response)
        form = hxs.select("//form[@id='form1']")
        data = {}
        for el in form.select(".//input"):
            key = el.select("@name").extract()
            value = el.select("@value").extract()
            if key:
                key = key[0]
                if not key.startswith('__'):
                    continue
                if value:
                    value = value[0]
                else:
                    value = ''
                data[key] = value

        for el in form.select(".//select"):
            key = el.select("@name").extract()
            value = el.select(".//option[@selected]/@value").extract()
            if key:
                key = key[0]
                if value:
                    value = value[0]
                else:
                    value = ''
                data[key] = value
        data['__ASYNCPOST'] = 'true'
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ValidCar'] = 'rbYes'
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlMake'] = '0'
        data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlWidthL'
        data['ctl00$sp'] = \
             'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$upPanel|ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlWidthL'

        # use row to fill in data
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlWidthL'] = row['Width']
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlDiameterL'] = row['Rim']
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlProfileL'] = row['Aspect Ratio']

        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlSpeedL'] = 'V'
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvDiameter'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvProfile'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvSpeed'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvWidth'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtPostCodeL'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtPostCodeR'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtRegNo'] = ""
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtValidRegNo'] = ""

        req = FormRequest(
            response.url,
            formdata=sorted(data.items()),
            callback=self.parse2,
            errback=self.error_callback,
            dont_filter=True,
            meta={
                'row': row,
                'formdata': data
            })
        yield req

    def parse2(self, response):
        row = response.meta['row']
        data = self.get_post_data(response)

        data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlProfileL'
        data['ctl00$sp'] = \
             'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$upPanel|ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlProfileL'

        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlProfileL'] = row['Aspect Ratio']
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlWidthL'] = row['Width']

        req = FormRequest(
            response.url,
            formdata=sorted(data.items()),
            callback=self.parse3,
            errback=self.error_callback,
            dont_filter=True,
            meta={
                'row': row,
                'formdata': data
            })
        yield req

    def parse3(self, response):
        row = response.meta['row']
        data = self.get_post_data(response)

        data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$FindTyreSlider1$ddlDiameterL'
        data['ctl00$sp'] = \
             'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$upPanel|ctl00$ContentPlaceHolder1$FindTyreSlider1$ddlDiameterL'

        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlDiameterL'] = row['Rim']
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlProfileL'] = row['Aspect Ratio']
        data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlWidthL'] = row['Width']

        req = FormRequest(
            response.url,
            formdata=sorted(data.items()),
            callback=self.parse4,
            errback=self.error_callback,
            dont_filter=True,
            meta={
                'row': row,
                'formdata': data
            })
        yield req

    def parse4(self, response):
        row = response.meta['row']
        data = self.get_post_data(response)

        data[u'__EVENTTARGET'] = u'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$lnkbtnSizeGo1'
        data[u'ctl00$sp'] = \
            u'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$upPanel|ctl00$ContentPlaceHolder1$FindTyreSliderHome1$lnkbtnSizeGo1'

        data[u'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlDiameterL'] = row['Rim']
        data[u'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlProfileL'] = row['Aspect Ratio']
        data[u'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlWidthL'] = row['Width']
        data[u'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtPostCodeL'] = '2151953'

        req = FormRequest(
            response.url,
            formdata=sorted(data.items()),
            callback=self.parse_make,
            errback=self.error_callback,
            dont_filter=True,
            meta={
                'row': row,
                'formdata': data
            })
        yield req

    def error_callback(self, failure):
        msg = "Failed to search row: %s" % self.current_row
        self.log("[AMAZON] %s" % msg)
        # self.errors.append(msg)
        self.prepare_for_next_row()

    def parse_make(self, response):
        hxs = HtmlXPathSelector(response)
        row = response.meta['row']
        form = hxs
        base_data = self.get_post_data(response)

        base_data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ValidCar'] = 'rbYes'
        base_data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$lnkbtnSizeGo2'
        base_data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtPostCodeL'] = row['IP code']

        base_data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlSpeedL'] = row['Speed rating']
        base_data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlDiameterL'] = row['Rim']
        base_data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlProfileL'] = row['Aspect Ratio']
        base_data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlWidthL'] = row['Width']
        base_data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$txtPostCodeL'] = '2151953'

        rewrite_keys = [
            (
                'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlWidthL',
                'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvWidth'),
            (
                'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlProfileL',
                'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvProfile'),
            (
                'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlDiameterL',
                'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvDiameter'),
            (
                'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlSpeedL',
                'ctl00$ContentPlaceHolder1$FindTyreSliderHome1$hvSpeed'),
        ]
        for field1, field2 in rewrite_keys:
            base_data[field2] = base_data[field1]

        if not self.makes:
            makes = form.select(".//select[@id='ddlMake']/option/@value").extract()
            self.makes = [x for x in makes if x != '0']

        for i, make in enumerate(self.makes):
            if make in self.current_row_processed_makes:
                continue
            self.log("Crawling row for make: %s" % make)
            self.current_row_processed_makes.add(make)
            data = base_data.copy()

            data['ctl00$ContentPlaceHolder1$FindTyreSliderHome1$ddlMake'] = make

            req = FormRequest(response.url,
                              formdata=sorted(data.items()),
                              callback=self.pre_parse_search,
                              dont_filter=True,
                              meta={
                                  'row': response.meta['row'],
                                  'formdata': data
                              })
            yield req
            return
        self.prepare_for_next_row()

    def pre_parse_search(self, response):
        yield Request('http://www.cartyres.com/tyre-selection?source=home&op=manual-selection',
                      dont_filter=True,
                      callback=self.parse_search,
                      meta={
                            'row': response.meta['row'],
                            'formdata': response.meta['formdata'],
                      })

    def _get_next_page_req(self, response):
        hxs = HtmlXPathSelector(response)

        if len(hxs.select("//div[@class='item_paging']/ul/li")) > 2:
            self.log("[CARTYRES] More than 2 pages: %s" % response.meta['row'])

        form = hxs.select("//form[@id='form1']")
        data = {}
        for el in form.select(".//input"):
            key = el.select("@name").extract()
            value = el.select("@value").extract()
            if key:
                key = key[0]
                if not key.startswith('__'):
                    continue
                if value:
                    value = value[0]
                else:
                    value = ''
                data[key] = value

        for el in form.select(".//select"):
            key = el.select("@name").extract()
            value = el.select(".//option[@selected]/@value").extract()
            if key:
                key = key[0]
                if value:
                    value = value[0]
                else:
                    value = ''
                data[key] = value

        data['__ASYNCPOST'] = 'false'
        data['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$rptPaging$ctl01$btnPage'
        data['ctl00$ContentPlaceHolder1$chkAll'] = 'on'
        data['ctl00$ContentPlaceHolder1$hdnIsSwitch'] = 'false'
        data['ctl00$sp'] = 'ctl00$ContentPlaceHolder1$UpdatePanel1|ctl00$ContentPlaceHolder1$rptPaging$ctl01$btnPage'

        req = FormRequest(response.url,
                          formdata=data,
                          callback=self.parse_search,
                          dont_filter=True,
                          meta={
                              'row': response.meta['row'],
                              'formdata': response.meta['formdata'],
                              'next_page': True
                          })
        yield req

    def parse_search(self, response):
        # data = {
        #     'width': response.meta['formdata']['ctl00$ContentPlaceHolder1$FindTyreSlider1$hvWidth'],
        #     'rim': response.meta['formdata']['ctl00$ContentPlaceHolder1$FindTyreSlider1$hvDiameter'],
        #     'aspect_ratio': response.meta['formdata']['ctl00$ContentPlaceHolder1$FindTyreSlider1$hvProfile'],
        #     'speed_rating': response.meta['formdata']['ctl00$ContentPlaceHolder1$FindTyreSlider1$hvSpeed'],
        #     'make': response.meta['formdata']['ctl00$ContentPlaceHolder1$FindTyreSlider1$ddlMake'],
        # }
        # self.log("[[TESTING]] Parsing data: %s" % str(data))
        for p in self.extract_products(response):
            self.current_make_prods.add(p['identifier'])
            yield p

        # Next page
        if not response.meta.get('next_page'):
            # self.log("[[TESTING]] Crawling next page")
            for r in self._get_next_page_req(response):
                yield r
        else:
            # check if products are the same as in previous make
            same_products = all([x in self.prev_make_prods for x in self.current_make_prods]) and all(
                [x in self.current_make_prods for x in self.prev_make_prods])
            if same_products:
                self.log("[CARTYRES] The same products are collected for current make. Skipping next makes")
                # finish with this row
                self.prepare_for_next_row()
            else:
                if self.prev_make_prods:
                    self.log("[CARTYRES] Different products for make: %s" % response.meta['formdata']['ctl00$ContentPlaceHolder1$FindTyreSlider1$ddlMake'])
                # save current prods as prev make prods
                self.prepare_for_next_make()

    def extract_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@class="listcontPART"]//div[@class="conprcbx"]')
        for el in products:
            brand = el.select('./div[@class="dec_tyrebnt"]/p/b/text()').extract().pop().strip()

            pattern = "".join(el.select('./div[@class="dec_tyrebnt"]/p/text()').extract()).strip()

            # skip winter tyres
            if 'winter' in pattern.lower():
                continue

            xl, pattern = extract_reinforced(pattern)
            run_flat, pattern = extract_run_flat(pattern)
            res = parse_pattern(pattern)
            if not res:
                excludes = ['sport contact', 'advantage sport', 'expedia s02', 'zero rosso']
                if any([x in pattern.lower() for x in excludes]):
                    continue
                else:
                    msg = 'Could not parse pattern: %s' % fix_spaces(pattern).encode('utf-8')
                    self.log('[CARTYRES] %s' % msg)
                    self.errors.append(msg)
                    continue
            width, ratio, rim, load_rating, speed_rating, name = res

            identifier = el.select(".//p/@onclick").re("AddCarToShortList\('([^']*)',")

            url = self.start_urls[0]

            price = el.select('.//div[@class="dec_fittdbnt"]/h1/text()').extract().pop()
            price = fix_spaces(price)

            image_url = el.select('../..//div[@class="uptyre_prt"]/img/@src').extract()[0]

            man_mark = el.select('.//div[@class="bndLGO1"]/img/@title').extract()
            if man_mark:
                man_mark = man_mark[0]
                if not man_mark in self.man_marks:
                    self.man_marks.add(man_mark)
            else:
                man_mark = ''

            loader = ProductLoader(Product(), selector=hxs)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier.pop())
            loader.add_value('price', price)
            loader.add_value('url', url)
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

            if man_mark and man_mark in man_mark_mapping:
                man_code = man_mark_mapping[man_mark]
            else:
                man_code = ''
            metadata['manufacturer_mark'] = man_code

            metadata['full_tyre_size'] = '/'.join((width,
                                                   ratio,
                                                   rim,
                                                   load_rating,
                                                   speed_rating))

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


reinforced_regex = re.compile(r"reinforced", re.I)


def extract_reinforced(pattern):
    """
    >>> extract_reinforced(u'205/55R16\xa094V\xa0 Wet: Performance REINFORCED')
    (True, u'205/55R16 94V Wet: Performance')
    """
    xl = "No"
    pattern = fix_spaces(pattern)
    m = reinforced_regex.search(pattern)
    if m:
        xl = "Yes"
        pattern = pattern.replace(m.group(0), '')
        pattern = fix_spaces(pattern.strip())
    return xl, pattern


run_flat_regex = re.compile(r"Run flat", re.I)


def extract_run_flat(pattern):
    """
    >>> extract_run_flat(u'205/55R16 91V  Economy RUN FLAT')
    (True, u'205/55R16 91V Economy')
    """
    run_flat = "No"
    pattern = fix_spaces(pattern)
    m = run_flat_regex.search(pattern)
    if m:
        run_flat = "Yes"
        pattern = pattern.replace(m.group(0), '')
        pattern = fix_spaces(pattern.strip())
    return run_flat, pattern


tyre_pattern_regex1 = re.compile(r"(\d*)/(\d+\.?\d*)R(\d*) ([\d/]*)([a-zA-Z]{1}) (.*)$")
tyre_pattern_regex2 = re.compile(r"(\d*)/(\d+\.?\d*)R(\d*) ([\d/]*)([a-zA-Z]{1})$")


def parse_pattern(pattern):
    """
    >>> parse_pattern(u'205/55R16\xa091V')
    (u'205', u'55', u'16', u'91', u'V', '')
    >>> parse_pattern(u'205/55R16\xa091V\xa0Proxes CF2')
    (u'205', u'55', u'16', u'91', u'V', u'Proxes CF2')
    """
    pattern = fix_spaces(pattern)
    m = tyre_pattern_regex1.search(pattern)
    if m:
        width, ratio, rim, load_rating, speed_rating, name = m.groups()

        return width, ratio, rim, load_rating, speed_rating, name
    m = tyre_pattern_regex2.search(pattern)
    if m:
        width, ratio, rim, load_rating, speed_rating = m.groups()

        return width, ratio, rim, load_rating, speed_rating, ''
    return None