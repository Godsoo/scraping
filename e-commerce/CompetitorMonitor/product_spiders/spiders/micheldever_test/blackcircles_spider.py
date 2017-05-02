import os
import csv
import json
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import FormRequest
from scrapy.utils.response import get_base_url

from product_spiders.base_spiders.matcher import Matcher


from product_spiders.items import Product, ProductLoader

from micheldeveritems import MicheldeverMeta
from micheldeverutils import find_mts_stock_code, is_product_correct, get_speed_rating, find_brand_segment, \
    get_alt_speed, find_man_mark, unify_brand


HERE = os.path.abspath(os.path.dirname(__file__))

class BlackcirclesSpider(BaseSpider):
    name = 'blackcircles.com_test'
    allowed_domains = ['blackcircles.com']
    start_urls = ('http://www.blackcircles.com',)
    tyre_sizes = []

    errors = []

    def __init__(self, *args, **kwargs):
        super(BlackcirclesSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)

        with open(os.path.join(HERE, 'mtsstockcodes.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.tyre_sizes.append(row)

    def start_requests(self):
        for row in self.tyre_sizes:
            '''
            if row['Width'] != '255' or row['Aspect Ratio'] != '35' or row['Rim'] != '19':
                continue
            '''

            formdata = {
                'profile': row['Aspect Ratio'],
                'rim': row['Rim'],
                'speed': row['Speed rating'],
                'width': row['Width'],
                'displayall': '999',
                'delivery': '1'
            }
            yield FormRequest(
                'http://www.blackcircles.com/order/tyres/search',
                dont_filter=True,
                formdata=formdata,
                meta={
                    'row': row,
                    'delivery': formdata['delivery']
                },
                callback=self.parse
            )

            if row['Alt Speed']:
                formdata = {
                    'profile': row['Aspect Ratio'],
                    'rim': row['Rim'],
                    'speed': row['Alt Speed'],
                    'width': row['Width'],
                    'displayall': '999',
                    'delivery': '1'
                }
                yield FormRequest(
                    'http://www.blackcircles.com/order/tyres/search',
                    dont_filter=True,
                    formdata=formdata,
                    meta={
                        'row': row,
                        'delivery': formdata['delivery']
                    },
                    callback=self.parse
                )

    def parse(self, response):
        try:
            hxs = HtmlXPathSelector(response)
        except AttributeError:
            msg = 'Error getting selector on page for row: %s' % response.meta['row']
            self.log('[ERROR] %s' % msg)
            self.errors.append(msg)
            return

        row = response.meta['row']

        json_data = None
        for line in hxs.extract().split('\n'):
            if "JsonObject = " in line:
                json_data = json.loads(line.replace('JsonObject = ', '').replace('; \r', ''))

        products = json_data['Rest'] + json_data['Deals']

        collected_products = []

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
            fitting_method = 'Delivered'

            url = '/catalogue' + product_info['CatalogueUrl'] + '/f?tyre=' + str(product_info['PrimaryId'])
            loader.add_value('url', urljoin(get_base_url(response), url))

            image_url = product_info.get('ModelImageLarge')
            if not image_url:
                image_url = product_info.get('ModelImage')

            if image_url:
                image_url = image_url.split('src="')[-1].split('"')[0]
                loader.add_value('image_url', urljoin(get_base_url(response), image_url))

            loader.add_value('identifier', str(identifier) + '-' + fitting_method)
            price = product_info['SellingPrice']
            loader.add_value('price', price)

            spec = product_info['SpecificationName']

            metadata = MicheldeverMeta()
            # metadata['mts_stock_code'] = row['MTS Stockcode']
            metadata['aspect_ratio'] = row['Aspect Ratio']
            metadata['rim'] = row['Rim']
            metadata['speed_rating'] = spec.split()[-1]
            metadata['width'] = row['Width']

            metadata['fitting_method'] = fitting_method
            load_rating = product_info['LoadRatingName']
            metadata['load_rating'] = load_rating
            metadata['alternative_speed_rating'] = ''
            xl = product_info['Reinforced']
            metadata['xl'] = 'Yes' if xl else 'No'
            run_flat = product_info['RunFlat']
            metadata['run_flat'] = 'Yes' if run_flat else 'No'
            manufacturer_mark = product_info['Variant']
            if manufacturer_mark:
                manufacturer_mark = manufacturer_mark.split()[0].strip()

            metadata['manufacturer_mark'] = find_man_mark(manufacturer_mark) if manufacturer_mark else ''

            metadata['full_tyre_size'] = '/'.join((row['Width'],
                                                   row['Aspect Ratio'],
                                                   row['Rim'],
                                                   metadata['load_rating'],
                                                   metadata['speed_rating']))

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

            # Do not collect "Delivered" tyres
            # yield product

            product['price'] = product_info['FullyFittedPrice']
            fitting_method = 'Fitted'
            product['identifier'] = str(identifier) + '-' + fitting_method
            product['metadata']['fitting_method'] = fitting_method
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
            yield product

    def match_name(self, search_name, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold
