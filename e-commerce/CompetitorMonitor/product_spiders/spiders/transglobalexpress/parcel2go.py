# -*- coding: utf-8 -*-
import re
import json
import os.path
import xlrd
from copy import deepcopy

from scrapy import Spider
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoader
from utils import extract_brand

HERE = os.path.abspath(os.path.dirname(__file__))


class Parcel2go(Spider):
    name = "transglobalexpress-parcel2go.com"
    allowed_domains = ('parcel2go.com',)

    handle_httpstatus_list = [301, 302]

    start_urls = ['https://www.parcel2go.com']

    destinations = []
    weights = {}

    def __init__(self, *args, **kwargs):
        super(Parcel2go, self).__init__(*args, **kwargs)

        tge_file = os.path.join(HERE, 'transglobalexpress_products.xlsx')
        wb = xlrd.open_workbook(tge_file)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 16:
                continue

            row = sh.row(rownum)
            if row[4].value:
                self.weights[row[4].value] = int(row[3].value) if row[3].value else 0

        self.destinations = ['UK - Mainland', 'Netherlands', 'Germany', 'Spain', 'Denmark', 'Poland', 'Romania', 'USA',
                             'Australia', 'China', 'United Arab Emirates', 'Brazil']

    def parse(self, response):
        data_quotes = []
        url = 'https://www.parcel2go.com/quotes?col=219&dest=%s&p=%s~%s|10|10|10#/results'
        for destination in self.destinations:
            try:
                delivery_country = re.findall('Id&quot;:(\d+),&quot;Display&quot;:&quot;%s' % destination, response.body)[0]
            except IndexError:
                continue
            body = {'DeliveryTown': None, 'RequiresCommercialInvoice': True, 'CollectionPostcode': None,
                    'DeliveryPostcode': None, 'CollectionTown': None, 'CollectionDate': None,
                    'DeliveryCountry': delivery_country, 'CurrencyCode': 'GBP', 'CollectionCountry': 219,
                    'Parcels': []}
            for weight, parcel in self.weights.iteritems():
                if parcel:
                    body = {'DeliveryTown': None, 'RequiresCommercialInvoice': True, 'CollectionPostcode': None,
                            'DeliveryPostcode': None, 'CollectionTown': None, 'CollectionDate': None,
                            'DeliveryCountry': delivery_country, 'CurrencyCode': 'GBP', 'CollectionCountry': 219,
                            'Parcels': []}
                    final_weight = round(weight / float(parcel), 2)
                    for i in range(parcel):
                        parcel_data = {'Width': 10, 'Length': 10, 'Weight': final_weight, 'Height': 10}
                        body['Parcels'].append(parcel_data)
                    parcel_url = url % (delivery_country, parcel, str(final_weight))
                    data_quotes.append({'parcel_url': parcel_url, 'body': deepcopy(body), 'destination': destination,
                                        'weight': str(weight), 'destination_id': delivery_country})
                else:
                    body = {'DeliveryTown': None, 'RequiresCommercialInvoice': True, 'CollectionPostcode': None,
                            'DeliveryPostcode': None, 'CollectionTown': None, 'CollectionDate': None,
                            'DeliveryCountry': delivery_country, 'CurrencyCode': 'GBP', 'CollectionCountry': 219,
                            'Parcels': [{'Width': 10, 'Length': 10, 'Weight': weight, 'Height': 10}]}
                    parcel_url = url % (delivery_country, '1', str(weight))
                    data_quotes.append({'parcel_url': parcel_url, 'body': deepcopy(body), 'destination': destination,
                                        'weight': str(weight), 'destination_id': delivery_country})

        meta = {}
        meta['data_quotes'] = data_quotes[1:]
        meta['body'] = data_quotes[0]['body']
        meta['weight'] = data_quotes[0]['weight']
        meta['destination'] = data_quotes[0]['destination']
        meta['destination_id'] = data_quotes[0]['destination_id']
        yield Request(data_quotes[0]['parcel_url'], callback=self.parse_shipments, meta=meta)

    def parse_shipments(self, response):
        meta = response.meta

        verification_token = response.xpath('//input[@name="__RequestVerificationToken"]/@value').extract()[0]
        headers = {'Content-Type': 'application/json', 'RequestVerificationToken': verification_token}

        meta['shipping_type'] = ''
        meta['url'] = response.url
        yield Request('https://www.parcel2go.com/quotes/api/results/all', body=json.dumps(meta['body']),
                      headers=headers, method='POST', callback=self.parse_products, meta=meta)

    def parse_products(self, response):
        json_data = json.loads(response.body)
        products = json_data['Quotes']
        for product in products:
            loader = ProductLoader(Product(), selector=product)
            name = product['Service']['Name']
            weight = str(response.meta['weight'])
            loader.add_value('identifier', product['Service']['ServiceSlug'] + '-' + weight + '-' + response.meta['destination_id'])
            loader.add_value('sku', weight)
            loader.add_value('name', name + ' ' + response.meta['destination'])
            additional = product.get('AdditionalPrices')
            if additional:
                additional = additional[0]

            if additional and additional.get('Cover', 0) == 50:
                loader.add_value('price', additional['NetTotal'])
            else:
                loader.add_value('price', product['SubTotal'])
            loader.add_value('url', response.meta['url'])
            loader.add_value('image_url', '')
            loader.add_value('brand', extract_brand(name))
            loader.add_value('category', response.meta['destination'])
            item = loader.load_item()
            yield item

            if item['name'].startswith('UPS Standard'):
                item['name'] = 'Multi ' + item['name']
                item['identifier'] += '-multi'
                yield item

        data_quotes = response.meta.get('data_quotes', None)
        if data_quotes:
            meta = response.meta
            meta['data_quotes'] = data_quotes[1:]
            meta['body'] = data_quotes[0]['body']
            meta['weight'] = data_quotes[0]['weight']
            meta['destination'] = data_quotes[0]['destination']
            meta['destination_id'] = data_quotes[0]['destination_id']
            yield Request(data_quotes[0]['parcel_url'], callback=self.parse_shipments, meta=meta)
