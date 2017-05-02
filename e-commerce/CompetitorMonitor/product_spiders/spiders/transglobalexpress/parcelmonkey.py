# -*- coding: utf-8 -*-
import os.path
import json
import xlrd
from copy import deepcopy


from scrapy import Spider
from scrapy.http import Request, FormRequest
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter

from product_spiders.items import Product, ProductLoader
from utils import extract_brand

HERE = os.path.abspath(os.path.dirname(__file__))


class ParcelMonkey(Spider):
    name = "transglobalexpress-parcelmonkey.co.uk"
    allowed_domains = ('parcelmonkey.co.uk',)

    handle_httpstatus_list = [301, 302]

    start_urls = ['https://www.parcelmonkey.co.uk/quotev3.php?sub=boxes']

    destinations = []
    weights = {}

    rates_url = 'https://www.parcelmonkey.co.uk/quotev3.php?sub=boxes'

    def __init__(self, *args, **kwargs):
        super(ParcelMonkey, self).__init__(*args, **kwargs)

        tge_file = os.path.join(HERE, 'transglobalexpress_products.xlsx')
        wb = xlrd.open_workbook(tge_file)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 16:
                continue

            row = sh.row(rownum)
            if row[4].value:
                self.weights[row[4].value] = int(row[3].value) if row[3].value else 0

        self.destinations = ['United Kingdom', 'Netherlands', 'Germany', 'Spain', 'Denmark', 'Poland', 'Romania', 'USA',
                             'Australia', 'China', 'United Arab Emirates', 'Brazil']

    def parse(self, response):
        data_quotes = []
        for destination in self.destinations:
            try:
                delivery_country = response.xpath('//select[@id="destination"]/option[text()="'+destination+'"]/@value').extract()[0]
            except IndexError:
                continue
            for weight, parcel in self.weights.iteritems():
                formdata = [('ShipmentEmail', ''),
                            ('destination', delivery_country),
                            ('height[]', '10'),
                            ('length[]', '10'),
                            ('width[]', '10')]
                if parcel:
                    final_weight = round(weight / float(parcel), 2)
                    formdata += [('weight[]', str(final_weight))]
                    for i in range(parcel-1):
                        formdata += [('height[]', '10'), ('length[]', '10'), ('weight[]', str(final_weight)), ('width[]', '10')]
                    data_quotes.append({'formdata': deepcopy(formdata), 'destination': destination,
                                        'weight': str(weight), 'destination_id': delivery_country})
                else:
                    formdata += [('weight[]', str(weight))]
                    data_quotes.append({'formdata': deepcopy(formdata), 'destination': destination,
                                        'weight': str(weight), 'destination_id': delivery_country})

        meta = {}
        meta['data_quotes'] = data_quotes[1:]
        meta['dont_redirect'] = True
        meta['handle_httpstatus_list'] = [302]
        meta['formdata'] = data_quotes[0]['formdata']
        meta['weight'] = data_quotes[0]['weight']
        meta['destination'] = data_quotes[0]['destination']
        meta['destination_id'] = data_quotes[0]['destination_id']

        yield FormRequest(self.rates_url, dont_filter=True, formdata=meta['formdata'], callback=self.parse_quotes,
                          meta=meta)

    def parse_quotes(self, response):
        url = 'https://www.parcelmonkey.co.uk/quotev3.php?sub=compare'
        yield Request(url, dont_filter=True, callback=self.parse_products, meta=response.meta)

    def parse_products(self, response):
        products = response.xpath('//li[@class="quotev3__quote" and div[@class="quote__quote-price"]/h3]')
        for product in products:
            name = product.xpath('.//div[@class="quote__quote-service-info"]/h3/text()').extract()
            if name:
                loader = ProductLoader(Product(), selector=product)
                weight = str(response.meta['weight'])
                name = name[0].strip()
                brand_data = product.xpath('.//div[@class="quote__quote-buy"]/a/@href').extract()[0]
                brand_data = url_query_parameter(brand_data, 'serviceinfo', '')
                if not brand_data:
                    continue
                brand_data = json.loads(brand_data)
                brand = brand_data['carrier']
                loader.add_value('identifier', brand + '-' + name + '-' + weight + '-' + response.meta['destination_id'])
                loader.add_value('sku', weight)
                loader.add_value('name', brand + ' ' + name + ' ' + response.meta['destination'])
                price = product.xpath('.//div[@class="quote__quote-price"]/h3/text()').extract()
                loader.add_value('price', price)
                loader.add_value('url', "https://www.parcelmonkey.co.uk")
                loader.add_value('image_url', '')
                loader.add_value('brand', extract_brand(name))
                loader.add_value('category', response.meta['destination'])
                item = loader.load_item()
                yield item

        data_quotes = response.meta.get('data_quotes', None)
        if data_quotes:
            meta = response.meta
            meta['data_quotes'] = data_quotes[1:]
            meta['dont_redirect'] = True
            meta['formdata'] = data_quotes[0]['formdata']
            meta['weight'] = data_quotes[0]['weight']
            meta['destination'] = data_quotes[0]['destination']
            meta['destination_id'] = data_quotes[0]['destination_id']
            meta['handle_httpstatus_list'] = [302]
            yield FormRequest(self.rates_url, dont_filter=True, formdata=meta['formdata'], callback=self.parse_quotes,
                              meta=meta)
