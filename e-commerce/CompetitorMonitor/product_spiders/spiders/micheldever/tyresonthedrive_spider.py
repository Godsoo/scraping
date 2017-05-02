import os
import csv
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc

from product_spiders.items import Product, ProductLoader
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, get_alt_speed, \
    find_brand_segment, find_man_mark, unify_brand, is_run_flat

from micheldeveritems import MicheldeverMeta


HERE = os.path.abspath(os.path.dirname(__file__))


class TyresOnTheDriveSpider(BaseSpider):
    name = 'tyresonthedrive.com'
    allowed_domains = ['tyresonthedrive.com']
    start_urls = ('https://www.tyresonthedrive.com/search/',)
    tyre_sizes = []
    new_old_names = {}
    brands = []
    manually_matched = []

    collected_identifiers = []

    def __init__(self, *args, **kwargs):
        super(TyresOnTheDriveSpider, self).__init__(*args, **kwargs)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

        with open(os.path.join(HERE, 'tyresonthedrive_name_changes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.new_old_names[row['new_name']] = row['old_name']

        self.brands = [row['Brand'] for row in self.tyre_sizes]

    def start_requests(self):
        url = 'https://www.tyresonthedrive.com/tyresearchstep1.aspx/PrepStep2FromTyreSearch'
        for row in self.tyre_sizes:
            tyre_size = row['Width'] + '_' + row['Aspect Ratio'] + '_' + row['Rim'] + '_' + row['Load rating']
            params = {'enteredPostcode': 'CV470RB', 'selectedTyreFromSize': tyre_size}
            req = Request(url,
                          method='POST',
                          dont_filter=True,
                          body=json.dumps(params),
                          headers={'Content-Type':'application/json'},
                          meta={'row':row})
            yield req

    def parse(self, response):
        base_url = get_base_url(response)
        # url = json.loads(response.body)['d']
        url = 'https://www.tyresonthedrive.com/search/choose/2/'
        yield Request(urljoin_rfc(base_url, url), callback=self.parse2, dont_filter=True)

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)
        search_id = hxs.select('//div[@id="stsid"]/text()').extract().pop()
        url = "https://www.tyresonthedrive.com/tyresearchstep2.aspx/Search"
        req = Request(url,
                      method='POST',
                      dont_filter=True,
                      body='{"tyreSearchedID": "%s"}' % search_id,
                      headers={'Content-Type':'application/json'},
                      callback=self.parse_products,
                      meta=response.meta)
        yield req

    def parse_products(self, response):
        json_data = json.loads(response.body)
        products = json.loads(json_data.get('d'))

        for product_el in products:
            loader = ProductLoader(item=Product(), selector=product_el)

            try:
                brand = product_el[u'ProductManufacturer'][u'TyreManufacturerName']
            except:
                brand = ''

            winter_tyre = product_el[u'ProductAttributes'][u'IsWinter']
            # skip winter tyres
            if winter_tyre:
                continue
            for tyre_brand in self.brands:
                if tyre_brand.upper() == brand.strip().upper():
                    brand = tyre_brand

            try:
                full_name = product_el[u'ProductTreadPattern'][u'TreadName']
            except:
                full_name = ''
            # Fix name changes
            if full_name in self.new_old_names:
                full_name = self.new_old_names[full_name]

            loader.add_value('name', full_name)
            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            identifier = product_el.get('TyreID')
            loader.add_value('url', 'https://www.tyresonthedrive.com')
            image_url = 'https://www.tyresonthedrive.com/img/treads/' + product_el[u'ProductTreadPattern'][u'TreadPatternImage'] + '.jpg'
            loader.add_value('image_url', image_url)
            loader.add_value('identifier', identifier)

            price = product_el[u'CheapestPriceTwoDay'][u'OneTyrePriceIncVat']
            if not price:
                loader.add_value('stock', 0)
            loader.add_value('price', price)

            metadata = MicheldeverMeta()

            metadata['aspect_ratio'] = str(product_el[u'ProductAttributes'][u'Profile'])
            metadata['rim'] = str(product_el[u'ProductAttributes'][u'Rim'])
            metadata['speed_rating'] = str(product_el[u'ProductAttributes'][u'Speed'])
            metadata['load_rating'] = str(product_el[u'ProductAttributes'][u'Load'])
            metadata['width'] = str(product_el[u'ProductAttributes'][u'Section'])
            metadata['fitting_method'] = 'Fitted'
            metadata['alternative_speed_rating'] = ''
            metadata['xl'] = 'Yes' if product_el[u'ProductAttributes'][u'IsExLoad'] else 'No'
            run_flat_found = is_run_flat(full_name)
            metadata['run_flat'] = 'Yes' if product_el[u'ProductAttributes'][u'IsRunFlat'] or run_flat_found else 'No'

            man_mark = product_el[u'ProductAttributes'][u'OEMFitment']
            metadata['manufacturer_mark'] = find_man_mark(man_mark) if man_mark else ''

            metadata['full_tyre_size'] = '/'.join((metadata['width'],
                                                   metadata['aspect_ratio'],
                                                   metadata['rim'],
                                                   metadata['load_rating'],
                                                   metadata['speed_rating']))
            product = loader.load_item()
            product['metadata'] = metadata

            if not is_product_correct(product):
                continue

            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)

            if product['identifier'] not in self.collected_identifiers:
                self.collected_identifiers.append(product['identifier'])
            elif not product['price']:
                continue
            else:
                yield product
