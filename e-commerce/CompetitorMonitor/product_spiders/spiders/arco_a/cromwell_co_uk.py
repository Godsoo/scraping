# -*- coding: utf-8 -*-
import json

from scrapy.http import Request
from urlparse import urljoin

from product_spiders.base_spiders.primary_spider import PrimarySpider
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class CromwellCoUkSpider(PrimarySpider):
    name = 'cromwell.co.uk'
    allowed_domains = ['cromwell.co.uk']
    start_urls = ('http://www.cromwell.co.uk/',)

    # website_id = 245

    csv_file = 'cromwell_crawl.csv'
    
    base_url = 'https://www.cromwell.co.uk/'
    
    category_url = 'https://restapi.cromwell.co.uk/v1.0/search?categoryId=%s'
    family_url = 'https://restapi.cromwell.co.uk/v1.0/search?familyId=%s'
    product_url = 'https://restapi.cromwell.co.uk/v1.0/products?sku=%s'

    def parse(self, response):
        data = response.xpath('//script/text()').re('window.__initialValues = ({.+})')
        data = json.loads(data[0])
        token = data['initialState']['auth']['jwtToken']
        self.headers = {'Authorization': token}
        categories = data['initialState']['categories']
        for category in categories:
            for cat_id in category['subcategories']:
                yield Request(self.category_url %cat_id, headers=self.headers, callback=self.parse_category)
                
    def parse_category(self, response):
        data = json.loads(response.body)
        for category in data['categories']:
            if not category['childCategories']:
                yield response.request.replace(dont_filter=True)
                return
            for child_category in category['childCategories']:
                cat_id = child_category['id']
                yield Request(self.category_url %cat_id, headers=self.headers, callback=self.parse_category)
                if 'families' not in child_category:
                    continue
                for family in child_category['families']:
                    product_skus = ','.join(family['products'])
                    yield Request(self.product_url %product_skus, headers=self.headers, callback=self.parse_products)

    def parse_products(self, response):
        data = json.loads(response.body)
        for product in data:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', product['sku'])
            loader.add_value('sku', product['sku'])
            loader.add_value('url', urljoin(self.base_url, product['sku']))
            loader.add_value('name', product['name'])
            price = product['price']['specialOfferPrice'] or product['price']['standardListPrice']
            if product['price']['standardBreak1Qty'] == 1 and product['price']['standardBreak1Price']:
                price = min(product['price']['standardBreak1Price'], price)
            loader.add_value('price', price)
            loader.add_value('category', product['category']['categoryName'])
            if product['mediaContent']:
                image_url = product['mediaContent'][0].get('mainPicture') or product['mediaContent'][0]['otherPictures1']
                image_url = image_url['productImage']['lowResolution']
                loader.add_value('image_url', image_url)
            loader.add_value('brand', product['brand']['brandName'])
            if price < 50:
                loader.add_value('shipping_cost', '4.99')
            loader.add_value('stock', product['stock']['quantity'])
            yield loader.load_item()
        
    def errback(self, failure, meta, url, callback):
        retry_no = int(meta.get('retry_no', 0))
        if retry_no < 10:
            retry_no += 1
            meta_copy = meta.copy()
            meta_copy['retry_no'] = retry_no
            yield Request(
                url,
                meta=meta_copy,
                callback=callback,
                errback=lambda failure, meta=meta_copy,
                url=url, callback=callback: self.errback(failure, meta, url, callback),
                dont_filter=True)
