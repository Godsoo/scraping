import os
import csv
import re
import urllib
from urlparse import urljoin as urljoin_rfc, unquote as url_unquote

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, find_brand_segment, \
    get_alt_speed, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))


class TyreTradersSpider(BaseSpider):
    name = 'tyretraders.com_test'
    allowed_domains = ['tyretraders.com']
    start_urls = ('http://www.tyretraders.com',)
    tyre_sizes = []
    all_man_marks = {}

    download_delay = 0.1

    def __init__(self, *args, **kwargs):
        super(TyreTradersSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.search_history = set()

    def _get_history_key(self, search_params):
        key = "%(width)s-%(rim)s-%(aspect_ratio)s-%(speed_rating)s" % search_params
        return key

    def check_in_history(self, search_params):
        if self._get_history_key(search_params) in self.search_history:
            return True
        return False

    def add_to_history(self, search_params):
        self.search_history.add(self._get_history_key(search_params))

    def start_requests(self):
        for i, row in enumerate(self.tyre_sizes):
            for speed_rating in [row['Speed rating'], row['Alt Speed']]:
                if not speed_rating:
                    continue

                search_params = {
                    'width': row['Width'],
                    'aspect_ratio': row['Aspect Ratio'],
                    'rim': row['Rim'],
                    'speed_rating': speed_rating
                }
                if self.check_in_history(search_params):
                    continue

                self.add_to_history(search_params)

                formdata = {
                    'width': search_params['width'],
                    'ratio': search_params['aspect_ratio'],
                    'rim': search_params['rim'],
                    'man': 'All',
                    'flat': 'False',
                    'filter': 'Price',
                    'ftype': 'Ascending',
                    'pricing': '2',
                    'cat': 'All',
                    'speed': search_params['speed_rating'],
                    'Loading': 'All',
                    'tyreType': 'All'
                }
                params = urllib.urlencode(formdata)
                yield Request('http://www.tyretraders.com/tyresearchresults.aspx?' + params,
                              dont_filter=True,
                              meta={'formdata': formdata, 'search_params': search_params},
                              callback=self.parse_pages)

    def parse_pages(self, response):
        hxs = HtmlXPathSelector(response)
        pages = hxs.select('//a[contains(@id, "rptPages2_ct")]/@href').extract()
        for page in pages:
            page = page.replace("javascript:__doPostBack('", '').replace("','')", '')
            formdata = {
                '__EVENTTARGET': page,
                '__EVENTARGUMENT': ''
            }
            yield FormRequest.from_response(response,
                                            formdata=formdata,
                                            dont_filter=True,
                                            dont_click=True,
                                            meta=response.meta,
                                            callback=self.parse_list)

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #products
        products = hxs.select('//div[@style="background-color:Black; width:546px; text-align:center;"]')
        for product in products:
            tyre_type = product.select('.//img[contains(@id, "_icoCategory")]/@title').extract()
            if tyre_type:
                if tyre_type[0].strip() == 'WINTER TYRES':
                    continue
            url = product.select('.//div[@title="Tyre Details"]/a/@href').extract()[0]
            url = urljoin_rfc(base_url, url)
            if product.select('.//img[contains(@id, "PriceBuster")]'):
                self.log("Product has no price: %s" % url)
                continue
            price = product.select('.//span[contains(@id, "_productprice")]/text()').extract()[0]
            meta = response.meta
            meta['price'] = price
            meta['retry'] = 0
            yield Request(url, meta=meta, callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        search_params = response.meta['search_params']
        formdata = response.meta['formdata']
        loader = ProductLoader(item=Product(), selector=hxs)
        title = hxs.select('//div[@class="rightpanel"]//h1/text()').extract()[0]
        title = ' '.join(title.split())
        tyre_params = "{}/{}R{}".format(search_params['width'], search_params['aspect_ratio'], search_params['rim'])
        parts = title.partition(tyre_params)
        brand = parts[0].strip()
        load_rating = parts[2].strip().split(formdata['speed'])[0].strip()
        name = title.partition('Fuel Effic')[0].replace('~', '').strip()
        name = name.replace('{} {} {}{} '.format(brand, tyre_params, load_rating, formdata['speed']), '')
        brand = brand.title()
        if 'goodrich' in brand.lower():
            brand = 'BFG'
        loader.add_value('brand', unify_brand(brand))

        if 'www.tyretraders.com' in name or tyre_params not in title:
            meta = response.meta
            meta['retry'] += 1
            if meta['retry'] < 10:
                yield Request(response.url, callback=self.parse, meta=meta, dont_filter=True)
            else:
                self.log('Giving up retrying to reload the product: {}'.format(response.url))
        else:
            price = response.meta.get('price')
            loader.add_value('price', price)
            identifier = response.url.split("|")[-1].split(".")[0]
            identifier = url_unquote(identifier)
            # identifier = hxs.select('//*[@id="hf_itemid"]/@value').extract()[0]
            loader.add_value('identifier', identifier)
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            loader.add_value('url', response.url)
            image_url = hxs.select('//div[@class="rightpanel"]//img[@style=" max-width:450px;"]/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = search_params['aspect_ratio']
            metadata['rim'] = search_params['rim']
            metadata['speed_rating'] = search_params['speed_rating']
            metadata['width'] = search_params['width']
            metadata['fitting_method'] = 'Fitted'
            metadata['load_rating'] = load_rating
            #metadata['alternative_speed_rating'] = ''
            result, name = remove_whole_word('XL', name)
            result1, name = remove_whole_word('RF', name)
            metadata['xl'] = 'Yes' if result or result1 else 'No'
            result, name = remove_whole_word('runflat', name)
            metadata['run_flat'] = 'Yes' if result else 'No'

            man_code = ''
            for code, man_mark in self.all_man_marks.iteritems():
                result, name = remove_whole_word(code, name)
                if result:
                    man_code = man_mark
                    break
            metadata['manufacturer_mark'] = man_code

            loader.add_value('name', name)

            metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                   metadata['aspect_ratio'],
                                                   metadata['rim'],
                                                   load_rating,
                                                   metadata['speed_rating']))
                                                   #metadata['alternative_speed_rating']))

            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                return

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            new_speed_rating = get_speed_rating(product)
            new_alt_speed = get_alt_speed(product)
            product['metadata']['alternative_speed_rating'] = new_alt_speed if new_alt_speed else \
                product['metadata']['speed_rating'] if product['metadata']['speed_rating'] != new_speed_rating else ''
            product['metadata']['speed_rating'] = new_speed_rating

            yield product


def remove_whole_word(w, text):
    if w == '*':
        for word in [' *', ' * ', '* ']:
            if word in text:
                text = text.replace(word, '', 1)
                return True, text
        return False, text
    match = re.compile(r'\b({0})\b'.format(re.escape(w)), flags=re.IGNORECASE).search(text)
    if match:
        text = ' '.join((text[:match.start()] + text[match.end():]).split())
        return True, text
    else:
        return False, text
