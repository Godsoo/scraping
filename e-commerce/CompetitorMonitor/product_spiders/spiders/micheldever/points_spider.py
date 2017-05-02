import re
import os
import csv
from scrapy.spider import Spider, Request
from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader
from micheldeveritems import MicheldeverMeta
from micheldeverutils import (
    find_mts_stock_code,
    is_product_correct,
    find_brand_segment,
    unify_brand, is_run_flat,
)


HERE = os.path.abspath(os.path.dirname(__file__))


class PointSSpider(Spider):
    name = 'micheldever-point-s.co.uk'
    allowed_domains = ['point-s.co.uk']
    start_urls = ('http://www.point-s.co.uk/',)
    tyre_sizes = []
    brands = []
    all_man_marks = {}

    def __init__(self, *args, **kwargs):
        super(PointSSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        self.brands = [row['Brand'] for row in self.tyre_sizes]

        self.processed_rows = {}

    def start_requests(self):
        for row in self.tyre_sizes:
            if self.check_row_is_processed(row):
                continue

            self.add_row_to_history(row)

            meta = {'row': row}
            xl = ''
            if row['XL'] == 'XL':
                xl = 'Y'
                meta['xl'] = True

            run_flat = ''
            if row['Run Flat'] == 'RF':
                run_flat = 'Y'
                meta['run_flat'] = True

            url = 'http://www.point-s.co.uk/tyres?s=&width=' + row['Width'] + '&profile=' + row['Aspect Ratio'] + '&size=' + row['Rim'] + '&speed=' + row['Speed rating'] + '&paginate=true&runflat=' + run_flat + '&extra_load=' + xl
            yield Request(url, dont_filter=True, meta=meta)

            if row['Alt Speed']:
                url = 'http://www.point-s.co.uk/tyres?s=&width=' + row['Width'] + '&profile=' + row['Aspect Ratio'] + '&size=' + row['Rim'] + '&speed=' + row['Alt Speed'] + '&paginate=true&runflat=' + run_flat + '&extra_load=' + xl
                yield Request(url, dont_filter=True, meta=meta)

    def get_row_key(self, row):
        fields_to_save = ['Width', 'Rim', 'Aspect Ratio', 'Speed rating', 'Alt Speed', 'XL', 'Run Flat']
        return tuple([row[x] for x in fields_to_save])

    def check_row_is_processed(self, row):
        key = self.get_row_key(row)
        if self.processed_rows.get(key):
            return True
        return False

    def add_row_to_history(self, row):
        key = self.get_row_key(row)
        self.processed_rows[key] = True

    def parse(self, response):
        row = response.meta['row']

        products = response.xpath('//div[contains(@class, "product-recommended")]')
        products += response.xpath('//div[@class="product-section"]/div[contains(@class, "product")]')
        for product_el in products:
            loader = ProductLoader(item=Product(), selector=product_el)

            brand = product_el.xpath('.//input[@name="brand"]/@value').extract()
            brand = brand[0] if brand else ''

            for tyre_brand in self.brands:
                if tyre_brand.upper() == brand.strip().upper():
                    brand = tyre_brand

            full_name = ''.join(product_el.xpath('.//h2/text()').extract())
            if not full_name:
                continue

            full_name_splt = re.split(brand, full_name, flags=re.I)
            tyre_code = full_name_splt[0]
            name = ' '.join(full_name_splt[1:]).strip()
            tyre_code = tyre_code.strip()
            name = name.strip()
            loader.add_value('name', name)

            # loader.add_value('name', full_name.split(brand)[-1])
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            identifier = product_el.xpath('.//input[@name="prodCode"]/@value').extract()
            if identifier:
                identifier = identifier[0]
            else:
                self.log('Product without identifier')
                search_params = '/'.join([row['Aspect Ratio'], row['Rim'], row['Width'], row['Alt Speed']])
                self.log('Search parameters: ' + search_params)
                return

            loader.add_value('url', response.url)
            image_url = product_el.xpath('.//div[contains(@class, "product-im")]/img/@src').extract()
            if image_url:
                loader.add_value('image_url', response.urljoin(image_url[0]))
            loader.add_value('identifier', identifier)

            price = ''.join(product_el.xpath('.//*[@class="price"]//text()').re(r'[\d\.,]+'))

            if not price:
                continue

            loader.add_value('price', price)

            metadata = MicheldeverMeta()

            metadata['aspect_ratio'] = row['Aspect Ratio']
            metadata['rim'] = row['Rim']

            speed = re.search('(\s\d+\w+\s)', full_name)
            speed_rating = speed.group().strip()[-1] if speed else ''
            load_rating = speed.group().strip()[:-1] if speed else ''

            metadata['speed_rating'] = speed_rating
            metadata['load_rating'] = load_rating

            metadata['width'] = row['Width']

            metadata['fitting_method'] = 'Fitted'
            metadata['alternative_speed_rating'] = ''
            metadata['xl'] = 'Yes' if 'XL' in full_name.upper() else 'No'
            run_flat_found = is_run_flat(full_name)
            metadata['run_flat'] = 'Yes' if 'RUNFLAT' in full_name.upper() or run_flat_found else 'No'

            metadata['manufacturer_mark'] = self._get_manufacturer_code(full_name)

            metadata['full_tyre_size'] = '/'.join((row['Width'],
                                                   row['Aspect Ratio'],
                                                   row['Rim'],
                                                   metadata['load_rating'],
                                                   metadata['speed_rating']))

            try:
                fuel, grip, noise = map(unicode.strip,
                    product_el.xpath('.//div[contains(@class, "feature-image") or contains(@class, "feature-block")]'
                                     '//span[@class="icon-text"]/text()').extract())
            except:
                fuel = ''
                grip = ''
                noise = ''

            metadata['fuel'] = fuel
            metadata['grip'] = grip
            metadata['noise'] = noise

            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            yield product

        next_page = response.xpath(u'//ul[@class="pagination"]//a[contains(text(), ">")]/@data-url').extract()
        if next_page:
            yield Request(next_page[0], dont_filter=True, meta=response.meta)

    def _get_manufacturer_code(self, name):
        name = name.upper().strip()
        for code, manufacturer_mark in self.all_man_marks.items():
            if code not in name:
                continue

            if code in map(unicode.strip, name.split(' ')) or code == '*':
                return manufacturer_mark

        return ''

    def match_name(self, search_name, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold
