import os
import re
import csv
import base64
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest, Request
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))


class TyrebookersSpider(BaseSpider):
    name = 'tyrebookers.com'
    allowed_domains = ['tyrebookers.com']
    start_urls = ('http://www.tyrebookers.com/',)
    tyre_sizes = []
    all_man_marks = {}
    custom_man_marks = {}
    # download_delay = 30
    thread1_done = True
    thread2_done = True
    thread3_done = True
    widths = []
    profiles = []
    rims = []

    def __init__(self, *args, **kwargs):
        super(TyrebookersSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)
        self.tyre_sizes = self.tyre_sizes[::-1]

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.already_processed = []

        self.custom_man_marks[' Merc'] = 'MO'
        self.custom_man_marks[' BMW'] = '*'
        self.custom_man_marks[' Audi'] = 'AO'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        self.widths = hxs.select('//select[@id="ddlWidthR"]/option/@value').extract()
        self.profiles = hxs.select('//select[@id="ddlProfileR"]/option/@value').extract()
        self.rims = hxs.select('//select[@id="ddlDiameterR"]/option/@value').extract()
        for x in self.next_search():
            yield x

    def next_search(self):
        if self.thread1_done and self.thread2_done and self.thread2_done:
            for i, row in enumerate(self.tyre_sizes, 1):
                good_params = row['Width'] in self.widths and row['Aspect Ratio'] in self.profiles and row['Rim'] in self.rims
                if not good_params:
                    continue
                if row['MTS Stockcode'] in self.already_processed:
                    continue
                self.already_processed.append(row['MTS Stockcode'])

                self.log("Searching for: %s. Params are: %s, %s, %s" % (row['MTS Stockcode'], row['Width'], row['Aspect Ratio'], row['Rim']))
                yield Request('http://www.tyrebookers.com/',
                              meta={'row': row, 'dont_merge_cookies': True},
                              callback=self.parse1,
                              dont_filter=True,
                              cookies={})
                break
        else:
            return

    def parse1(self, response):
            row = response.meta.get('row')
            formdata = {'ctl00$MainContent$FindTyreSlider1$ValidCar': 'rbYes',
                        'ctl00$MainContent$FindTyreSlider1$btnGo1Right': ' Go >',
                        'ctl00$MainContent$FindTyreSlider1$ddlDiameterL': row['Rim'],
                        'ctl00$MainContent$FindTyreSlider1$ddlDiameterR': row['Rim'],
                        'ctl00$MainContent$FindTyreSlider1$ddlMake': '112',
                        'ctl00$MainContent$FindTyreSlider1$ddlProfileL': row['Aspect Ratio'],
                        'ctl00$MainContent$FindTyreSlider1$ddlProfileR': row['Aspect Ratio'],
                        'ctl00$MainContent$FindTyreSlider1$ddlSpeedL': 'All',
                        'ctl00$MainContent$FindTyreSlider1$ddlSpeedR': 'All',
                        'ctl00$MainContent$FindTyreSlider1$ddlWidthL': row['Width'],
                        'ctl00$MainContent$FindTyreSlider1$ddlWidthR': row['Width'],
                        'ctl00$MainContent$FindTyreSlider1$hdnSide': 'RIGHT',
                        'ctl00$MainContent$FindTyreSlider1$hvFDiameter': row['Rim'],
                        'ctl00$MainContent$FindTyreSlider1$hvFProfile': row['Aspect Ratio'],
                        'ctl00$MainContent$FindTyreSlider1$hvFSpeed': 'All',
                        'ctl00$MainContent$FindTyreSlider1$hvFWidth': row['Width'],
                        'ctl00$MainContent$FindTyreSlider1$hvRDiameter': row['Rim'],
                        'ctl00$MainContent$FindTyreSlider1$hvRProfile': row['Aspect Ratio'],
                        'ctl00$MainContent$FindTyreSlider1$hvRSpeed': 'All',
                        'ctl00$MainContent$FindTyreSlider1$hvRWidth': row['Width'],
                        'ctl00$MainContent$FindTyreSlider1$txtRegNumberL': '',
                        'ctl00$MainContent$FindTyreSlider1$txtValidRegNo': '',
                        'ctl00$MainContent$FindTyreSlider1$wtxtRegNumberL_ClientState': '',
                        'ctl00$MainContent$ucReview1$rptReview$ctl00$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl01$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl02$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl03$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl04$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl05$hdnRating': '4',
                        'ctl00$MainContent$ucReview1$rptReview$ctl06$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl07$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl08$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl09$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl10$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl11$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl12$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl13$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl14$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl15$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl16$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl17$hdnRating': '5',
                        'ctl00$MainContent$ucReview1$rptReview$ctl18$hdnRating': '4',
                        'ctl00$MainContent$ucReview1$rptReview$ctl19$hdnRating': '5',
                        'ctl00$sp': 'ctl00$MainContent$FindTyreSlider1$UpdatePanel1|ctl00$MainContent$FindTyreSlider1$btnGo1Right',
                        }
            yield FormRequest.from_response(response,
                                            formdata=formdata,
                                            dont_filter=True,
                                            dont_click=True,
                                            meta={'row': row},
                                            callback=self.parse2)

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)
        formdata = {'ctl00$MainContent$FindTyreSlider1$btnGo2Right': ' Go >'}
        cars = hxs.select('//select[@id="ddlMake"]/option/@value').extract()
        for car in cars:
            if car != '0':
                formdata['ctl00$MainContent$FindTyreSlider1$btnGo2Right'] = car
                yield FormRequest.from_response(response,
                                                formdata=formdata,
                                                dont_filter=True,
                                                dont_click=True,
                                                meta=response.meta,
                                                callback=self.parse3)
                break

    def parse3(self, response):
        self.thread1_done = self.thread2_done = self.thread3_done = True
        hxs = HtmlXPathSelector(response)
        mid = hxs.select('//*[@id="MainContent_MidTyre"]').extract()
        if mid:
            self.thread1_done = False
            formdata = {'ctl00$sp': 'ctl00$MainContent$UpdatePanel1|ctl00$MainContent$MidTyre',
                        '__EVENTTARGET': 'ctl00$MainContent$MidTyre'}
            meta = response.meta.copy()
            meta['thread'] = 'thread1_done'
            yield FormRequest.from_response(response,
                                            formdata=formdata,
                                            dont_filter=True,
                                            dont_click=True,
                                            meta=meta,
                                            callback=self.parse_list)
        bud = hxs.select('//*[@id="MainContent_BudTyre"]').extract()
        if bud:
            self.thread2_done = False
            formdata = {'ctl00$sp': 'ctl00$MainContent$UpdatePanel1|ctl00$MainContent$BudTyre',
                        '__EVENTTARGET': 'ctl00$MainContent$BudTyre'}
            meta = response.meta.copy()
            meta['thread'] = 'thread2_done'
            yield FormRequest.from_response(response,
                                            formdata=formdata,
                                            dont_filter=True,
                                            dont_click=True,
                                            meta=meta,
                                            callback=self.parse_list)
        pre = hxs.select('//*[@id="MainContent_PreTyre"]').extract()
        if pre:
            self.thread3_done = False
            response.meta['thread'] = 'thread3_done'
            for x in self.parse_list(response):
                yield x

    def parse_list(self, response):
        setattr(self, response.meta.get('thread'), True)
        hxs = HtmlXPathSelector(response)
        vs_data = hxs.select('//input[@name="__VIEWSTATE"]/@value').extract()[0]
        identifiers = parse_identifiers(vs_data)

        products = hxs.select('//div[@class="main-list"]//div[@class="group conti-box"]')
        for product_el in products:
            identifier = identifiers.pop(0)
            specif = product_el.select('.//span[@class="blue"]//div/text()').extract()
            # skip winter tyres
            if 'WINTER' in specif:
                continue
            loader = ProductLoader(item=Product(), selector=product_el)
            title = product_el.select('.//div[@class="conti-gray"]/text()').extract()[0]
            # identifier = title.split()
            title = title.strip().split('\r\n')
            name = title[-1].strip()
            width = title[0].split("/")[0].strip()
            ratio = title[0].split("/")[1].replace("R", "").strip()
            rim = title[1].strip()
            rating = title[2].strip()
            results = re.search(r"((?:\d{1,3}/)*(?:\d{1,3}))([A-Z]{1,2}\d?)", rating)
            if results:
                load_rating = results.group(1)
                speed_rating = results.group(2)
            else:
                load_rating = speed_rating = ''
            brand = product_el.select('.//div[@class="black-conti"]/text()').extract()[0].strip()
            brand = brand.title()
            if 'bfg' in brand.lower():
                brand = 'BFG'
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            price = product_el.select('.//h4[@class="prc"]/text()').extract()[0]
            loader.add_value('price', extract_price(price))
            # identifier = brand.replace(' ', '') + ''.join(identifier)
            loader.add_value('identifier', identifier)
            loader.add_value('url', '')
            image_url = product_el.select('.//div[@class="sec-img"]/img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))

            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = ratio
            metadata['rim'] = rim
            metadata['speed_rating'] = speed_rating
            metadata['width'] = width
            metadata['fitting_method'] = 'Fitted'
            metadata['load_rating'] = load_rating
            # metadata['alternative_speed_rating'] = ''

            metadata['xl'] = 'Yes' if 'REINFORCED' in specif else 'No'
            run_flat_found = is_run_flat('%s %s' % (name, ' '.join(specif)))
            metadata['run_flat'] = 'Yes' if 'RUN FLAT' in specif or run_flat_found else 'No'

            man_code = ''
            for code, man_mark in self.all_man_marks.iteritems():
                result, name = cut_name(code, name)
                if result:
                    man_code = man_mark
                    break
            if not man_code:
                for code, man_mark in self.custom_man_marks.iteritems():
                    if name.endswith(code):
                        name = name.partition(code)[0]
                        man_code = man_mark
                        break
            metadata['manufacturer_mark'] = man_code

            loader.add_value('name', name)
            metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                   metadata['aspect_ratio'],
                                                   metadata['rim'],
                                                   load_rating,
                                                   speed_rating))
                                                   # metadata['alternative_speed_rating']))

            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            yield product
        for x in self.next_search():
            yield x


def parse_identifiers(vs_data):
    vs = base64.decodestring(vs_data)
    s = repr(vs)
    identifiers = []
    _s = s.split('dd\\x02\\x1c\\x0f\\x15\\x01')[0:-1]
    if not _s:
        _s = s.split('dd\\x02\\x1e\\x0f\\x15\\x01')[0:-1]
    for identifier in _s:
        _id = identifier[identifier.rfind('\\x05') + 4:]
        if _id.startswith('\\x'):
            _id = _id[4:]
        _id = _id.replace('\\r', '')
        identifiers.append(_id)
    return identifiers


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
