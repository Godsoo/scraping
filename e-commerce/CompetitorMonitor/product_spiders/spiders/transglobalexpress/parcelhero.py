# -*- coding: utf-8 -*-
import os.path
import xlrd
import json
import time

from scrapy import Spider
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoader
from utils import extract_brand

HERE = os.path.abspath(os.path.dirname(__file__))


class ParcelHero(Spider):
    name = "transglobalexpress-parcelhero.com"
    allowed_domains = ('parcelhero.com',)
    start_urls = ['https://www.parcelhero.com/home/getcountrylist']

    destinations = []
    weights = {}

    def __init__(self, *args, **kwargs):
        super(ParcelHero, self).__init__(*args, **kwargs)

        tge_file = os.path.join(HERE, 'transglobalexpress_products.xlsx')
        wb = xlrd.open_workbook(tge_file)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 16:
                continue

            row = sh.row(rownum)
            if row[4].value:
                self.weights[row[4].value] = int(row[3].value) if row[3].value else 0

        self.destinations = ['Great Britain', 'Holland (The Netherlands)', 'Germany', 'Spain', 'Denmark', 'Poland',
                             'Romania', 'United States', 'Australia', 'China', 'United Arab Emirates', 'Brazil']

        self.destination_ids = {}

    def parse(self, response):
        data = json.loads(response.body)

        destination_ids = {}
        for country in data:
            destination_ids[country['CountryName']] = country['CountryId']

        data_quotes = []
        for destination in self.destinations:
            delivery_country = destination_ids[destination.upper()]
            quote = '207,,%s,,%s,%s,10,10,10,postcode,cms,kgs,N,postcode,,,%s'
            shipment_url = 'https://www.parcelhero.com/shipment/quote?Q='
            for weight, parcel in self.weights.iteritems():
                if parcel:
                    final_weight = round(weight / float(parcel), 2)
                    formdata = {'LeadSourceType': '',
                                'QuoteData': quote % (str(delivery_country), str(parcel), str(final_weight), str(parcel)),
                                'SavedData': '', 'UpgradeOption': '', 'data': ''}
                    data_quotes.append({'shipment_url': shipment_url + quote % (str(delivery_country), str(parcel), str(final_weight), str(parcel)),
                                        'formdata': formdata, 'destination': destination,
                                        'weight': str(weight), 'destination_id': delivery_country})
                else:
                    formdata = {'LeadSourceType': '',
                                'QuoteData': quote % (str(delivery_country), '1', str(weight), '1'),
                                'SavedData': '', 'UpgradeOption': '', 'data': ''}
                    data_quotes.append({'shipment_url': shipment_url + quote % (str(delivery_country), '1', str(weight), '1'),
                                        'formdata': formdata, 'destination': destination,
                                        'weight': str(weight), 'destination_id': delivery_country})

        meta = {}
        meta['data_quotes'] = data_quotes[1:]
        meta['formdata'] = data_quotes[0]['formdata']
        meta['weight'] = data_quotes[0]['weight']
        meta['destination'] = data_quotes[0]['destination']
        meta['destination_id'] = data_quotes[0]['destination_id']

        yield Request(data_quotes[0]['shipment_url'], callback=self.parse_quotes,
                      meta=meta)

    def parse_quotes(self, response):
        meta = response.meta
        meta['url'] = response.url
        url = 'https://www.parcelhero.com/shipment/AsyncGetCheapestListNew/B,' + str(int(round(time.time() * 1000)))
        yield FormRequest(url, dont_filter=True, formdata=meta['formdata'], callback=self.parse_products, meta=meta)

    def parse_products(self, response):
        products = response.xpath('//div[@class="services-block-items"]/div[contains(@class, "service-block-item")]')
        for product in products:
            brand = product.xpath('.//p[@class="hl"]/text()').re('provided by (.*)')[0]
            name = ' '.join(map(lambda x: x.strip(), product.xpath('.//div[@class="sb-body"]/h3//text()').extract()))
            loader = ProductLoader(Product(), selector=product)
            weight = str(response.meta['weight'])
            destination_id = str(response.meta['destination_id'])
            loader.add_value('identifier', brand + '-' + name + '-' + weight + '-' + destination_id)
            loader.add_value('name', brand + ' ' + name + ' ' + response.meta['destination'])
            price = product.xpath('.//h3//span[@class="shipCost"]/text()').extract()
            loader.add_value('price', price)
            loader.add_value('sku', weight)
            loader.add_value('url', response.meta['url'])
            loader.add_value('image_url', '')
            loader.add_value('brand', extract_brand(name))
            loader.add_value('category', response.meta['destination'])
            item = loader.load_item()
            yield item

            if item['name'].startswith('DPD Classic'):
                item['name'] = 'Multi ' + item['name']
                item['identifier'] += '-multi'
                yield item

        data_quotes = response.meta.get('data_quotes', None)
        if data_quotes:
            meta = response.meta
            meta['data_quotes'] = data_quotes[1:]
            meta['formdata'] = data_quotes[0]['formdata']
            meta['weight'] = data_quotes[0]['weight']
            meta['destination'] = data_quotes[0]['destination']
            meta['destination_id'] = data_quotes[0]['destination_id']
            yield FormRequest(data_quotes[0]['shipment_url'], dont_filter=True, formdata=meta['formdata'],
                              callback=self.parse_quotes, meta=meta)
