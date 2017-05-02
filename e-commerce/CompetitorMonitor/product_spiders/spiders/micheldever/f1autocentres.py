import os
import csv
import re
from urlparse import urljoin

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


class EtyresSpider(BaseSpider):
    name = 'f1autocentres.co.uk'
    allowed_domains = ['f1autocentres.co.uk']
    # start_urls = ('http://www.f1autocentres.co.uk',)
    tyre_sizes = []
    all_man_marks = {}
    search_history = []

    # download_delay = 0.1

    def __init__(self, *args, **kwargs):
        super(EtyresSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

    def start_requests(self):
        for row in self.tyre_sizes:
            hist = "{}{}{}{}".format(row['Width'], row['Aspect Ratio'], row['Rim'], row['Speed rating'])
            if hist in self.search_history:
                continue
            self.search_history.append(hist)
            formdata = {'form': '2',
                        'tyreWidth': row['Width'],
                        'tyreProfile': row['Aspect Ratio'],
                        'tyreWheel': row['Rim'],
                        'tyreSpeed': row['Speed rating']}
            yield FormRequest('https://www.f1autocentres.co.uk/tyre-results.php',
                              formdata=formdata,
                              meta={'row': row},
                              dont_filter=True,
                              callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        row = response.meta['row']
        products = hxs.select('//div[contains(@class, "tyreResult")]')
        for product in products:
            winter = product.select('.//li[@class="cw"]')
            # skip winter tyres
            if winter:
                continue
            loader = ProductLoader(item=Product(), selector=product)
            title = ' '.join(map(unicode.strip, product.select('.//div[@class="tyreName"]//text()').extract())).strip()
            brand = product.select('@data-brand').extract()
            if not brand:
                continue
            brand = brand[0].title()
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            title = title[len(brand):].strip()
            results = re.search(r"\b((?:\d{2,3}/)*(?:\d{2,3}))\s?([A-Z]{1,2}\d?)\b", title)
            if results:
                load_rating = results.group(1)
                speed_rating = results.group(2)
                name = title[:results.start(1)]
                title = title[results.end(2):]
            else:
                load_rating = ''
                speed_rating = row['Speed rating']
                name = title
                title = ''
            price = ''.join(product.select('.//div[@class="tyrePrice"]//text()').extract()).strip()
            loader.add_value('price', price)
            identifier = product.select('.//input[@name="id"]/@value').extract()[0]
            loader.add_value('identifier', identifier)
            loader.add_value('url', '')
            image_url = product.select('.//div[@class="tyreImage"]/img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin(get_base_url(response), image_url[0]))

            metadata = MicheldeverMeta()
            metadata['aspect_ratio'] = row['Aspect Ratio']
            metadata['rim'] = row['Rim']
            metadata['speed_rating'] = speed_rating
            metadata['width'] = row['Width']
            metadata['fitting_method'] = 'Fitted'
            metadata['load_rating'] = load_rating
            # metadata['alternative_speed_rating'] = ''
            metadata['xl'] = 'Yes' if bool(product.select('./@data-types').re(r'xl')) else 'No'
            run_flat_found = is_run_flat(title)
            metadata['run_flat'] = 'Yes' if bool(product.select('./@data-types').re(r'rf')) or run_flat_found else 'No'
            specif = product.select('.//ul//li/@class').extract()
            man_code = ''
            if 'bmw' in specif:
                man_code = '*'
            elif 'mer' in specif:
                man_code = 'MO'
            elif 'aud' in specif:
                man_code = 'AO'
            elif 'por' in specif:
                man_code = 'NO'

            for code, man_mark in self.all_man_marks.iteritems():
                result, name = cut_name(code, name)
                if result:
                    if man_code == '':
                        man_code = man_mark
                    break
            if man_code == '':
                for code, man_mark in self.all_man_marks.iteritems():
                    result, title = cut_name(code, title)
                    if result:
                        man_code = man_mark
                        break
            metadata['manufacturer_mark'] = man_code
            result, name = cut_name('XL', name)
            loader.add_value('name', name)

            metadata['full_tyre_size'] = '/'.join((row['Width'],
                                                   row['Aspect Ratio'],
                                                   row['Rim'],
                                                   load_rating,
                                                   speed_rating))
                                                   # metadata['alternative_speed_rating']))

            prod = loader.load_item()
            prod['metadata'] = metadata

            if not is_product_correct(prod):
                continue

            prod['metadata']['mts_stock_code'] = find_mts_stock_code(prod, spider_name=self.name, log=self.log)

            yield prod


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
