# -*- coding: utf-8 -*-
import os.path
import xlrd
from copy import deepcopy


from scrapy import Spider
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoader
from utils import extract_brand

HERE = os.path.abspath(os.path.dirname(__file__))


class TransglobalExpress(Spider):
    name = "transglobalexpress-transglobalexpress.co.uk"
    allowed_domains = ('transglobalexpress.co.uk',)

    handle_httpstatus_list = [301, 302]

    start_urls = ['http://www.transglobalexpress.co.uk/']

    destinations = []
    weights = {}

    rates_url = 'http://www.transglobalexpress.co.uk/Quote/Rates'

    def __init__(self, *args, **kwargs):
        super(TransglobalExpress, self).__init__(*args, **kwargs)

        tge_file = os.path.join(HERE, 'transglobalexpress_products.xlsx')
        wb = xlrd.open_workbook(tge_file)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 16:
                continue

            row = sh.row(rownum)
            if row[4].value:
                self.weights[row[4].value] = int(row[3].value) if row[3].value else 0

        for rownum in xrange(sh.nrows):
            if rownum < 16:
                continue

            row = sh.row(rownum)
            if row[2].value:
                self.destinations.append(row[2].value)

    def parse(self, response):
        rates_url = 'http://www.transglobalexpress.co.uk/Quote/Rates'
        data_quotes = []
        for destination in self.destinations:
            try:
                delivery_country = response.xpath('//select[@id="DeliveryCountryId"]/option[text()="'+destination+'"]/@value').extract()[0]
            except IndexError:
                continue
            weights = response.meta['weights'] if response.meta.get('weights', None) else self.weights
            for weight, parcel in self.weights.iteritems():
                formdata = [('CollectionCountryId', '231'),
                            ('CollectionPostCodeInput', ''),
                            ('DeliveryCountryId', delivery_country),
                            ('DeliveryPostCodeInput', ''),
                            ('Height', '10'),
                            ('ItemType', '0'),
                            ('Length', '10'),
                            ('Width', '10')]
                if parcel:
                    final_weight = round(weight / float(parcel), 2)
                    formdata += [('Weight', str(final_weight)), ('NoItems', str(parcel))]
                    for i in range(parcel-1):
                        formdata += [('Height', '10'), ('Length', '10'), ('Weight', str(final_weight)), ('Width', '10')]
                    data_quotes.append({'formdata': deepcopy(formdata), 'destination': destination,
                                        'destination_id': delivery_country, 'weight': weight})
                else:
                    formdata += [('NoItems', '1'), ('Weight', str(weight))]
                    data_quotes.append({'formdata': deepcopy(formdata), 'destination': destination,
                                        'destination_id': delivery_country, 'weight': weight})

        meta = {}
        meta['data_quotes'] = data_quotes[1:]
        meta['dont_redirect'] = True
        meta['handle_httpstatus_list'] = [302]
        meta['formdata'] = data_quotes[0]['formdata']
        meta['weight'] = data_quotes[0]['weight']
        meta['destination'] = data_quotes[0]['destination']
        meta['destination_id'] = data_quotes[0]['destination_id']

        meta['data_quotes'] = data_quotes[1:]
        yield FormRequest(self.rates_url, dont_filter=True, formdata=meta['formdata'], callback=self.parse_quotes,
                          meta=meta)

    def parse_quotes(self, response):
        url = 'http://www.transglobalexpress.co.uk/quote/quote/'
        yield Request(url, dont_filter=True, callback=self.parse_products, meta=response.meta)

    def parse_products(self, response):
        products = response.xpath('//table[@id="quotationTbl"]//tr')
        for product in products:
            name = product.xpath('.//td[@class="serviceName"]//span[@class="name"]/text()').extract()
            if name:
                loader = ProductLoader(Product(), selector=product)
                name = name[0].strip()
                weight = str(response.meta['weight'])
                name = name + ' ' + response.meta['destination']
                loader.add_value('name', name)
                loader.add_value('sku', weight)
                try:
                    identifier = product.xpath('.//a/@onclick').re('btnBook_OnClick\((\d+), ')[0]
                except IndexError:
                    self.log('ERROR: NO IDENTIFIER FOR :' + response.meta['destination'] + '   ' + str(response.meta['formdata']))
                    continue
                loader.add_value('identifier', identifier+'-'+response.meta['destination_id'])
                price = product.xpath('.//td[@class="highlight"]/b/text()').re('(\d+.\d+)')[0]
                loader.add_value('price', price)
                loader.add_value('url', "http://www.transglobalexpress.co.uk")
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
