# -*- coding: utf-8 -*-

"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4779-worten---new-site---amazonite/details

Extract all products from the ('electrodomesticos', 'escritorio', 'tecnologia') categories.
"""

import json
from copy import deepcopy
from decimal import Decimal, ROUND_UP

from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request


def format_price(price, rounding=None):
    if price is None:
        return Decimal('0.00')

    return price.quantize(Decimal('0.01'), rounding=rounding or ROUND_UP)


class AmazoniteSpider(BaseSpider):
    name = "sonae-amazonite.pt"
    allowed_domains = ["amazonite.pt"]
    start_urls = ["https://www.amazonite.pt"]

    categories = {}

    per_page = 120

    categories_url = 'https://www.amazonite.pt/produtos?cs={}'
    pagination_url = 'https://www.amazonite.pt/web/api/portal/ecproducts?cs={category}&language=pt&' \
                     'pbwuid={pbwuid}&' \
                     '{json_fields}'
    pagination_fields = {'page': 1,
                         'pageSize': per_page,
                         'skip': 0,
                         'sort': [],
                         'take': per_page}
    headers = {'Accept': '*/*',
                          'Content-Type': 'application/json; charset=utf-8',
                          'X-Requested-With': 'XMLHttpRequest'}
    image_url = 'https://www.amazonite.pt/_portal/_widgets/ecommerce/products/UserControls/ImageHandler.ashx?' \
                'path=Files/PortalReady/v000&size=150&ID={image_id}'
    product_url = 'https://www.amazonite.pt/produtos-detalhes?ref={product_id}'
    category_names_url = 'https://www.amazonite.pt/web/api/portal/ecTreeCategories?cs={category}'

    '''
    def start_requests(self):
        categories = ('electrodomesticos', 'escritorio', 'tecnologia')
        for category in categories:
            yield Request(self.pagination_url.format(category=category,
                                                     json_fields=json.dumps(self.pagination_fields)),
                          meta={'fields': self.pagination_fields.copy(),
                                'category': category},
                          headers=self.headers)
    '''
    def parse(self, response):
        pbwuid = response.xpath('//input[@data-field="pbwuid"]/@value').extract()[0]
        categories = ('electrodomesticos', 'escritorio', 'tecnologia')
        for category in categories:
            yield Request(self.pagination_url.format(category=category,
                                                     pbwuid=pbwuid,
                                                     json_fields=json.dumps(self.pagination_fields)),
                          callback=self.parse_products,
                          meta={'fields': self.pagination_fields.copy(),
                                'pbwuid': pbwuid,
                                'category': category},
                          headers=self.headers)


    def parse_products(self, response):
        data = json.loads(response.body)
        for item in data['Data']:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', item['Reference'])
            loader.add_value('sku', item['Reference'])
            loader.add_value('name', item['Name'])
            if item['OfferPriceWithTax'] and item['OfferPriceWithTax'] != item['PriceWithTax']:
                loader.add_value('price', format_price(Decimal(item['OfferPriceWithTax'])))
            else:
                loader.add_value('price', format_price(Decimal(item['PriceWithTax'])))
            loader.add_value('brand', item['BrandName'])
            loader.add_value('category', item['CategoryName'])
            loader.add_value('image_url', self.image_url.format(image_id=item['ImageID']))
            loader.add_value('url', self.product_url.format(product_id=item['Reference']))
            category_code = item['CategoryUniqueName']
            if category_code in self.categories:
                for category in self.categories[category_code]:
                    loader.add_value('category', category)
                    yield loader.load_item()
            else:
                product = loader.load_item()
                yield Request(self.category_names_url.format(category=category_code),
                              meta={'product': product,
                                    'category_code': category_code},
                              callback=self.parse_categories,
                              headers=self.headers,
                              dont_filter=True)

        metadata_ = deepcopy(response.meta)
        if metadata_['fields']['skip'] < data['Count'] and data['Data']:
            metadata_['fields']['skip'] += self.per_page
            metadata_['fields']['page'] += 1
            yield Request(self.pagination_url.format(category=metadata_['category'],
                                                     pbwuid=metadata_['pbwuid'],
                                                     json_fields=json.dumps(metadata_['fields'])),
                          callback=self.parse_products,
                          meta=metadata_,
                          headers=self.headers)

    def parse_categories(self, response):
        data = json.loads(response.body)
        category_code = response.meta.get('category_code')
        product = response.meta.get('product')
        self.categories[category_code] = [c['Name'] for c in data]
        loader = ProductLoader(item=product, response=response)
        for category in self.categories[category_code]:
            loader.add_value('category', category)
        yield loader.load_item()
