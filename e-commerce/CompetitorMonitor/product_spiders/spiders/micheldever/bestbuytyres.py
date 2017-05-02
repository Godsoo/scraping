# -*- coding: utf-8 -*-
import os
import re
import csv
from urlparse import urljoin as urljoin_rfc

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))


class BestBuyTyresSpider(BaseSpider):
    name = 'bestbuytyres.com'
    allowed_domains = ['bestbuytyres.co.uk']
    start_urls = ('http://www.bestbuytyres.co.uk',)
    tyre_sizes = []
    all_man_marks = {}
    brand_fixes = {}
    custom_man_marks = {}
    download_delay = 0.1

    handle_httpstatus_list = [500]

    def __init__(self, *args, **kwargs):
        super(BestBuyTyresSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.brand_fixes['Bridgestone'] = ["b'stone", 'b/stone', 'bridestone', 'bridgestohne', 'brridgestone']
        self.brand_fixes['Continental'] = ['conti', 'contiental', 'continenal', 'continntal', 'contintenal']
        self.brand_fixes['Dunlop'] = ['dlp']
        self.brand_fixes['Goodyear'] = ['g’year', 'g’yr', 'g/year', 'goodyea', 'gy', 'gyr']
        self.brand_fixes['Michelin'] = ['mich']
        self.brand_fixes['Pirelli'] = ['pir', 'pire', 'pireelli']
        # self.brand_fixes['Uniroyal'] = ['uni']
        self.custom_man_marks = {
            '(LEXUS FITMENT)': '',
            '()': '',
            '(BMW FITMENT)': '*',
            '(RAV 4)': '',
            '(BMW)': '*'
        }

        self.errors = []

    def parse(self, response):
        f = FormRequest('http://www.bestbuytyres.co.uk/branches/get-closest',
                        formdata={'postcode': 'B43 7BG'},
                        callback=self.parse2,
                        meta={'handle_httpstatus_list': [500],
                              'dont_retry': True})
        yield f

    def parse2(self, response):
        r = FormRequest('http://www.bestbuytyres.co.uk/tyres/get-widths', formdata={'branch': '104'},
                        callback=self.search_requests)
        yield r

    def search_requests(self, response):
        for row in self.tyre_sizes:
            formdata = dict()
            formdata['width'] = row['Width']
            formdata['profile'] = row['Aspect Ratio']
            formdata['rim'] = row['Rim']
            formdata['branch'] = '104'
            formdata['brand'] = '0'
            formdata['speed'] = '0'
            yield FormRequest('http://www.bestbuytyres.co.uk/tyres-search',
                              formdata=formdata,
                              dont_filter=True,
                              meta={'row': row},
                              callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        row = response.meta['row']

        products = hxs.select('//*[@id="tyreResults"]//tr[contains(@class, "tyre")]//td[@class != "gutter"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            title = product.select('.//p[@class="subTitle"]/text()').extract()
            if not title:
                continue
            title = ' '.join(title[0].split())

            parsed_title = parse_title_new(title)


            brand = parsed_title['brand']
            load_rating = parsed_title['load_rating']
            speed_rating = parsed_title['speed_rating']
            name = parsed_title['name']
            if not name or not brand:
                self.log("++++++++++++++++++++++++++++{}==================".format(title))
                # self.errors.append("Error parsing title: %s" % title)
            for fixed_brand, brand_spellings in self.brand_fixes.iteritems():
                if brand.lower() in brand_spellings:
                    brand = fixed_brand
                    break
            brand = brand.title()
            if brand not in self.brand_fixes:
                self.log('Wrong brand %s' % brand)
                continue
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            price = product.select('.//h6[@class="price"]/text()').extract()[0]
            price += product.select('.//h6[@class="price"]/sup/text()').extract()[0]
            loader.add_value('price', extract_price(price))
            identifier = product.select('./a[@class="btnBuy png_bg"]/@href').extract()[0]
            identifier = identifier.split('/')[-1]
            loader.add_value('identifier', identifier)
            loader.add_value('url', '')
            image_url = product.select('.//img[@class="tyreImg"]/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

            metadata = MicheldeverMeta()
            metadata['onsite_name'] = title
            metadata['aspect_ratio'] = row['Aspect Ratio']
            metadata['rim'] = row['Rim']
            metadata['speed_rating'] = speed_rating
            metadata['width'] = row['Width']
            metadata['fitting_method'] = 'Fitted'
            metadata['load_rating'] = load_rating

            self.log("===============matching================")
            self.log(str(name))

            metadata['manufacturer_mark'], name = filter_man_code(name, self.all_man_marks, self.custom_man_marks)
            self.log(str((metadata['manufacturer_mark'], name)))

            metadata['xl'], name = filter_xl(name)
            metadata['xl'] = "Yes" if metadata['xl'] else "No"
            self.log(str((metadata['xl'], name)))

            run_flat_found = is_run_flat(name)
            metadata['run_flat'], name = filter_run_flat(name)
            metadata['run_flat'] = "Yes" if metadata['run_flat'] or run_flat_found else "No"
            self.log(str((metadata['run_flat'], name)))

            self.log("===============/matching===============")

            if name.endswith('('):
                name = name[:-1]
            loader.add_value('name', name.strip())

            metadata['full_tyre_size'] = '/'.join((row['Width'],
                                                   row['Aspect Ratio'],
                                                   row['Rim'],
                                                   load_rating,
                                                   speed_rating))
                                                   # metadata['alternative_speed_rating']))

            fuel = product.select('.//div[@class="tyreLabel"]/span/img[contains(@src, "icon=fuel")]').re(r'rr=(\w)')
            metadata['fuel'] = fuel[0] if fuel else ''
            grip = product.select('.//div[@class="tyreLabel"]/span/img[contains(@src, "icon=wet")]').re(r'wg=(\w)')
            metadata['grip'] = grip[0] if grip else ''
            noise = product.select('.//div[@class="tyreLabel"]/span/img[contains(@src, "icon=noise")]').re(r'db=(\d+)')
            metadata['noise'] = noise[0] if noise else ''

            prod = loader.load_item()
            prod['metadata'] = metadata

            if not is_product_correct(prod):
                continue

            prod['metadata']['mts_stock_code'] = find_mts_stock_code(prod, spider_name=self.name, log=self.log)

            yield prod


def parse_title(text):
    """
    >>> res = parse_title('345/30ZR19 MICHELIN PILOT SPORT 98Y ZP (RUNFLAT)')
    >>> res['name']
    'PILOT SPORT ZP (RUNFLAT)'
    >>> res['load_rating']
    '98'
    >>> res['speed_rating']
    'Y'
    """
    res = {'brand': '', 'load_rating': '', 'speed_rating': '', 'name': ''}
    match = re.search(r"([0-9]{2,3}/?[0-9\.]{0,3}[\s]*[A-Z]{0,2}[\s]*[0-9]{2}[^\s]*)\s([^\s]*)", text.upper())
    if match:
        res['brand'] = match.group(2)
        title = text[match.end():].strip()
        match = None
        for match in re.finditer(r"((?:\d{1,3}/)*(?:\d{1,3}))([A-Z]{1,2}\d?)", title.upper()):
            pass
        if match:
            res['load_rating'] = match.group(1)
            res['speed_rating'] = match.group(2)
            res['name'] = ' '.join([title[:match.start()].strip(), title[match.end():].strip()])
        else:
            res['name'] = title
    return res

def parse_title_new(text):
    res = {'brand': '', 'load_rating': '', 'speed_rating': '', 'name': ''}
    try:
        parts = text.split(' ')
        load_rating = re.search('(\d{2,3}[A-Z])', ' '.join(parts[5:])).groups()[0]
        res['load_rating'] = load_rating[:-1]
        res['speed_rating'] = parts[3]
        res['brand'] = parts[4]
        res['name'] = ' '.join(parts[5:]).replace(load_rating, '')
        return res
    except:
        return res


def filter_xl(text):
    xl_possible_words = ['extraload', 'xl', 'xload']
    result = None
    for xl_word in xl_possible_words:
        temp_result, text = remove_whole_word(xl_word, text)
        if temp_result:
            result = True
    return result, text


def filter_run_flat(text):
    """
    >>> filter_run_flat('345/30ZR19 MICHELIN PILOT SPORT 98Y ZP (RUNFLAT)')
    (True, '345/30ZR19 MICHELIN PILOT SPORT 98Y')
    """
    rf_possible_words = ['run flat', 'run on flat', 'rof', 'rof', 'rft', 'zp', 'ssr', '(runflat)', 'runflat']
    result = None
    for rf_word in rf_possible_words:
        temp_result, text = remove_whole_word(rf_word, text)
        if temp_result:
            result = True

    return result, text


def filter_man_code(text, man_marks, custom_man_marks):
    man_code = ''
    for code, man_mark in man_marks.iteritems():
        result, text = remove_whole_word(code, text)
        if result:
            man_code = man_mark
            break
    if not man_code:
        for code, man_mark in custom_man_marks.iteritems():
            if text.endswith(code):
                text = text.partition(code)[0]
                man_code = man_mark
                break

    text = text.replace('()', '').strip()
    return man_code, text


def remove_whole_word(w, text):
    """
    >>> remove_whole_word('(runflat)', '345/30ZR19 MICHELIN PILOT SPORT 98Y ZP (RUNFLAT)')
    (True, '345/30ZR19 MICHELIN PILOT SPORT 98Y ZP')
    """
    if w == '*':
        for word in [' *', ' * ', '* ']:
            if word in text:
                text = text.replace(word, '', 1)
                return True, text
        if text.endswith('*'):
            text = text[:-1]
            return True, text
        return False, text
    match = re.compile(r'\b({0})\b'.format(re.escape(w)), flags=re.IGNORECASE).search(text)
    match2 = re.compile(r'\s({0})\s'.format(re.escape(w)), flags=re.IGNORECASE).search(text)
    match3 = re.compile(r'\s({0})$'.format(re.escape(w)), flags=re.IGNORECASE).search(text)
    if match:
        text = ' '.join((text[:match.start()] + text[match.end():]).split())
        return True, text
    elif match2:
        text = ' '.join((text[:match2.start()] + text[match2.end() - 1:]).split())
        return True, text
    elif match3:
        text = ' '.join((text[:match3.start()] + text[match3.end():]).split())
        return True, text
    else:
        return False, text
