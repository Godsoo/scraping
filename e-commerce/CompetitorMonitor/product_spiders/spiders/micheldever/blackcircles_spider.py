import os
import csv
import json
import time
from scrapy import Spider, FormRequest
from product_spiders.base_spiders.matcher import Matcher
from product_spiders.items import Product, ProductLoader
from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, find_brand_segment, \
    find_man_mark, unify_brand, is_run_flat


HERE = os.path.abspath(os.path.dirname(__file__))


class BlackcirclesSpider(Spider):
    name = 'blackcircles.com'
    allowed_domains = ['blackcircles.com']
    start_urls = ('http://www.blackcircles.com',)
    tyre_sizes = []

    errors = []
    seen_ids = set()

    def __init__(self, *args, **kwargs):
        super(BlackcirclesSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

    def start_requests(self):
        search_seen = set()
        for row in self.tyre_sizes:
            formdata = {
                'profile': row['Aspect Ratio'],
                'rim': row['Rim'],
                'speed': 'Any',
                'width': row['Width'],
                'displayall': '999',
                'delivery': '0',
            }

            search_key = '{}:{}:{}'.format(row['Aspect Ratio'], row['Rim'], row['Width'])
            if search_key not in search_seen:
                yield FormRequest(
                    'http://www.blackcircles.com/order/tyres/search',
                    dont_filter=True,
                    formdata=formdata,
                    meta={'row': row},
                    callback=self.parse
                )
                search_seen.add(search_key)
            else:
                self.log('Duplicate search: {}'.format(search_key))


    def parse(self, response):
        row = response.meta['row']

        json_data = None
        for line in response.body.split('\n'):
            if "JsonObject = " in line:
                json_data = json.loads(line.replace('JsonObject = ', '').replace('; \r', ''))

        products = json_data['Rest'] + json_data['Deals']

        collected_products = []

        self.log('Results found {} {}'.format(len(products), response.meta))
        for product_info in products:
            # skip winter tyres
            if product_info['WinterTyre']:
                continue

            loader = ProductLoader(item=Product(), selector=product_info)
            loader.add_value('name', product_info['ModelName'])
            brand = product_info['Manufacturer']

            loader.add_value('brand', unify_brand(brand))
            loader.add_value('category', find_brand_segment(loader.get_output_value('brand')))
            identifier = product_info['PrimaryId']
            fitting_method = 'Fitted'
            if str(identifier) + '-' + fitting_method in self.seen_ids:
                continue

            url = '/catalogue' + product_info['CatalogueUrl'] + '/f?tyre=' + str(product_info['PrimaryId'])
            loader.add_value('url', response.urljoin(url))

            image_url = product_info.get('ModelImageLarge')
            if not image_url:
                image_url = product_info.get('ModelImage')

            if image_url:
                image_url = image_url.split('src="')[-1].split('"')[0]
                loader.add_value('image_url', response.urljoin(image_url))

            spec = product_info['SpecificationName']
            metadata = MicheldeverMeta()
            # metadata['mts_stock_code'] = row['MTS Stockcode']
            metadata['aspect_ratio'] = row['Aspect Ratio']
            metadata['rim'] = row['Rim']
            metadata['speed_rating'] = spec.split()[-1]
            metadata['width'] = row['Width']

            load_rating = product_info['LoadRatingName']
            metadata['load_rating'] = load_rating
            metadata['alternative_speed_rating'] = ''
            xl = product_info['Reinforced']
            metadata['xl'] = 'Yes' if xl else 'No'
            run_flat_found = is_run_flat(product_info['ModelName'])
            run_flat = product_info['RunFlat']
            metadata['run_flat'] = 'Yes' if run_flat or run_flat_found else 'No'
            manufacturer_mark = product_info['Variant']
            if manufacturer_mark:
                manufacturer_mark = manufacturer_mark.split()[0].strip()

            full_tyre_size = '/'.join((row['Width'],
                                       row['Aspect Ratio'],
                                       row['Rim'],
                                       metadata['load_rating'],
                                       metadata['speed_rating']))
            # MOE Exception for this product
            if manufacturer_mark and 'MO EXTENDED' in product_info['Variant'].upper()\
               and product_info['ModelName'] == 'Potenza S001' and full_tyre_size == '245/40/18/97/Y':
                metadata['manufacturer_mark'] = 'MOE'
            else:
                metadata['manufacturer_mark'] = find_man_mark(manufacturer_mark) if manufacturer_mark else ''

            metadata['full_tyre_size'] = full_tyre_size

            try:
                metadata['fuel'] = product_info['TyreLabelFuel']['Score']
            except Exception:
                metadata['fuel'] = ''

            try:
                metadata['grip'] = product_info['TyreLabelWet']['Score']
            except Exception:
                metadata['grip'] = ''

            try:
                metadata['noise'] = product_info['TyreLabelNoise']['NoiseLevel']
            except Exception:
                metadata['noise'] = ''

            product = loader.load_item()
            product['metadata'] = metadata

            product['price'] = product_info['FullyFittedPrice']
            fitting_method = 'Fitted'
            product['identifier'] = str(identifier) + '-' + fitting_method
            product['metadata']['fitting_method'] = fitting_method

            t1 = time.time()
            if not is_product_correct(product):
                self.log('Search: {}'.format(str(response.meta)))
                self.seen_ids.add(str(identifier) + '-' + fitting_method)
                self.log('PRODUCT IS NOT CORRECT => %r' % product)
                continue
            t2 = time.time()
            self.log('Time taken by product correct: {}'.format(t2-t1))

            t1 = time.time()
            product['metadata']['mts_stock_code'] = find_mts_stock_code(product, spider_name=self.name, log=self.log)
            t2 = time.time()
            self.log('Time taken by mts stock: {}'.format(t2-t1))

            collected_products.append(product)

        min_price_products = {}
        for product in collected_products:
            key = "%s-%s-%s-%s-%s-%s-%s" % (
                product['brand'],
                product['name'],
                product['metadata']['fitting_method'],
                product['metadata']['full_tyre_size'],
                product['metadata']['xl'],
                product['metadata']['run_flat'],
                product['metadata']['manufacturer_mark']
            )
            if key in min_price_products:
                if product['price'] < min_price_products[key]['price']:
                    min_price_products[key] = product
            else:
                min_price_products[key] = product

        for product in min_price_products.values():
            self.seen_ids.add(product['identifier'])
            yield product

    def match_name(self, search_name, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold
