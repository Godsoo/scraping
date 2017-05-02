import re
import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, \
    get_speed_rating, get_alt_speed, find_brand_segment, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))


class HalfordsSpider(BaseSpider):
    name = 'halfordsautocentres.com'
    allowed_domains = ('halfordsautocentres.com',)
    start_urls = ('http://www.halfordsautocentres.com/',)

    all_man_marks = {}

    tyre_sizes = []

    def __init__(self, *args, **kwargs):
        super(HalfordsSpider, self).__init__(*args, **kwargs)

        with open(os.path.join(HERE, 'manmarks.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.all_man_marks[row['code']] = row['manufacturer_mark']

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

    def _get_manufacturer_code(self, name):
        name = name.upper()
        for code, manufacturer_mark in self.all_man_marks.items():
            if code not in name:
                continue

            if code in name.split(' ') or code == '*':
                return manufacturer_mark

        return ''

    def parse(self, response):
        yield Request('http://www.halfordsautocentres.com/webapp/wcs/stores/servlet/TyresLandingPageView?' +
                      'storeId=11602&langId=-1&catalogId=19253&categoryId=276255', callback=self.search)

    def search(self, response):
        for i, row in enumerate(self.tyre_sizes):
            url = "http://www.halfordsautocentres.com/webapp/wcs/stores/servlet/FindTyresCmd?" \
                  "storeId=11602&langId=-1&catalogId=19253&categoryId=276255&action=searchTyre&" \
                  "vrnExp=&sectionWidth=%(width)s&aspectRatio=%(aspect_ratio)s&rimDiameter=%(rim)s&" \
                  "speedRating=%(speed_rating)s&qualityPref=good_value&mileage=med&findTyres=Find+Tyres"

            url = url % {
                'width': row['Width'],
                'aspect_ratio': row['Aspect Ratio'],
                'rim': row['Rim'],
                'speed_rating': row['Speed rating']
            }

            yield Request(url, callback=self.parse_products, meta={'product_data': row})

            if row['Alt Speed']:
                url = "http://www.halfordsautocentres.com/webapp/wcs/stores/servlet/FindTyresCmd?" \
                  "storeId=11602&langId=-1&catalogId=19253&categoryId=276255&action=searchTyre&" \
                  "vrnExp=&sectionWidth=%(width)s&aspectRatio=%(aspect_ratio)s&rimDiameter=%(rim)s&" \
                  "speedRating=%(speed_rating)s&qualityPref=good_value&mileage=med&findTyres=Find+Tyres"

                url = url % {
                    'width': row['Width'],
                    'aspect_ratio': row['Aspect Ratio'],
                    'rim': row['Rim'],
                    'speed_rating': row['Alt Speed']
                }

                yield Request(url, callback=self.parse_products, meta={'product_data': row})

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)

        product_data = response.meta['product_data']
        width = product_data['Width']
        aspect_ratio = product_data['Aspect Ratio']
        rim = product_data['Rim']
        speed_rating = product_data['Speed rating']
        alt_speed = product_data['Alt Speed']

        name_reg = r'(.+?)\s*%s.+%s.?[\s]*([\d+ /]+)%s\s*(.*)' % (width, rim, speed_rating.upper())
        name_reg2 = r'(.+?)\s*%s.+%s.?[\s]*([\d+ /]+)%s\s*(.*)' % (width, rim, alt_speed.upper())
        name_reg3 = r'(.+?)\s*%s.+%s.?[\s]*(.*)' % (width, rim)
        products = hxs.select('//div[@id="product-listing"]//div[@class="product"]/..')
        for product_el in products:
            loader = ProductLoader(item=Product(), selector=product_el)
            try:
                url = product_el.select('.//div[@class="title"]/a/@href')[0].extract()
            except:
                continue
            loader.add_value('url', url)
            loader.add_value('identifier',
                             product_el.select(".//span[@class='addcompare']/input/@id").extract()[0].split(":")[1])
            # loader.add_value('identifier', re.search('productId_(\d+)_', url).groups()[0])
            loader.add_xpath('price', './/span[@class="prodPirce"]/text()')
            try:
                name = product_el.select('.//div[@class="title"]/a/text()')[0].extract()
            except:
                continue
            run_flat_found = is_run_flat(name)
            if not re.search(r'(\(.*\))', name):
                # name = name.replace('/', '')
                m = re.search(name_reg, name)
                if not m:
                    m = name_parts = re.search(name_reg2, name)
                if not m:
                    m = name_parts = re.search(name_reg3, name)

                if m:
                    name_parts = m.groups()
                else:
                    self.log('Failed parsing ' + name)
                    self.log('URL: ' + response.url)
                    self.log('Params: ' + ", ".join(map(str, [width, rim, speed_rating.upper()])))
                    continue
            else:
                name_parts = []
                name_parts.append(name.split()[0])
                load_rating_reg = re.search(r'(\d+)%s' % speed_rating.upper(), name)
                if not load_rating_reg:
                    load_rating_reg = re.search(r'(\d+)%s' % alt_speed.upper(), name)
                if not load_rating_reg:
                    self.log('Failed parsing ' + name)
                    self.log('URL: ' + response.url)
                    self.log('Params: ' + ", ".join(map(str, [width, rim, speed_rating.upper()])))
                    continue
                name_parts.append(load_rating_reg.groups()[0])
                name_parts.append(' '.join(name.split()[1:]).split('(')[0])

            loader.add_value('name', name_parts[-1].replace('XL', '').replace('ROF', '').replace('RFT', ''))
            brand = name_parts[0]
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            loader.add_xpath('image_url', './/a[contains(@class, "tyre")]/img/@src')
            m = MicheldeverMeta()
            m['aspect_ratio'] = aspect_ratio
            m['rim'] = rim
            m['width'] = width
            m['speed_rating'] = speed_rating.upper()
            m['load_rating'] = name_parts[1]
            if 'ROF' in name.upper() or 'RFT' in name.upper() or run_flat_found:
                m['run_flat'] = 'Yes'
            else:
                m['run_flat'] = 'No'

            if 'XL' in name.upper():
                m['xl'] = 'Yes'
            else:
                m['xl'] = 'No'

            m['full_tyre_size'] = '/'.join((m['width'],
                                            m['aspect_ratio'],
                                            m['rim'],
                                            m['load_rating'],
                                            m['speed_rating']))
                                            # m['alternative_speed_rating']))

            m['fitting_method'] = 'Fitted'
            m['manufacturer_mark'] = self._get_manufacturer_code(name_parts[-1])
            fuel = product_el.select('.//div[@class="legislationContainer"]/ul[@class="legislation"]/li/a[contains(@class, "fuel_")]/@class').re(r'fuel_(\w)')
            m['fuel'] = fuel[0] if fuel else ''
            grip = product_el.select('.//div[@class="legislationContainer"]/ul[@class="legislation"]/li/a[contains(@class, "grip_")]/@class').re(r'grip_(\w)')
            m['grip'] = grip[0] if grip else ''
            noise = product_el.select('.//div[@class="legislationContainer"]/ul[@class="legislation"]/li/a[contains(@class, "noise_")]/@class').re(r'_(\d+)')
            m['noise'] = noise[-1] if noise else ''

            product = loader.load_item()
            product['metadata'] = m

            if not is_product_correct(product):
                self.log('The product is not correct: %r' % product)
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            yield product

        next_page = hxs.select('//span[@class="nextlink"]/a/@href')
        if next_page:
            yield Request(next_page.extract()[0], callback=self.parse_products, meta=response.meta)
