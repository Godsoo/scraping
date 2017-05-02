# -*- coding: utf-8 -*-
import os.path
import xlrd
from copy import deepcopy


from scrapy import Spider
from scrapy.http import Request, FormRequest

from scrapy.utils.url import add_or_replace_parameter, url_query_parameter

from product_spiders.items import Product, ProductLoader
from utils import extract_brand

HERE = os.path.abspath(os.path.dirname(__file__))


class Interparcel(Spider):
    name = "transglobalexpress-interparcel.com"
    allowed_domains = ('interparcel.com',)
    start_urls = ['http://www.interparcel.com']

    rotate_agent = True
    download_delay = 4

    destinations = []
    weights = {}

    base_url = ('http://www.interparcel.com/quote/courier-quote2.php?booking_type=parcel&id_coll_city='
                '&id_coll_state=&id_coll_postcode=&id_coll_displaytext=&id_del_city=&id_del_state=&id_del_postcode='
                '&id_del_displaytext=&id_coll_country=UK&coll_text_search=&submit=Quote+Me!')

    def __init__(self, *args, **kwargs):
        super(Interparcel, self).__init__(*args, **kwargs)

        tge_file = os.path.join(HERE, 'transglobalexpress_products.xlsx')
        wb = xlrd.open_workbook(tge_file)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(sh.nrows):
            if rownum < 16:
                continue

            row = sh.row(rownum)
            if row[4].value:
                self.weights[row[4].value] = int(row[3].value) if row[3].value else 0

        self.destinations = ['UK', 'Netherlands', 'Germany', 'Spain', 'Denmark', 'Poland', 'Romania', 'USA',
                             'Australia', 'China', 'United Arab Emirates', 'Brazil']

    def parse(self, response):

        data_quotes = []
        for destination in self.destinations:
            for weight, parcel in self.weights.iteritems():
                if parcel:
                    url = self.base_url
                    url = add_or_replace_parameter(url, 'packagecount', parcel)
                    url = add_or_replace_parameter(url, 'id_del_country', destination)
                    parcel_weight = int(weight / parcel)
                    for i in range(parcel):
                        item_number = str(i + 1)
                        url = add_or_replace_parameter(url, 'length[%s]' % item_number, '10')
                        url = add_or_replace_parameter(url, 'width[%s]' % item_number, '10')
                        url = add_or_replace_parameter(url, 'height[%s]' % item_number, '10')
                        url = add_or_replace_parameter(url, 'weight[%s]' % item_number, str(parcel_weight))
                    data_quotes.append({'url':url, 'destination': destination, 'weight': weight})
                else:
                    url = self.base_url
                    url = add_or_replace_parameter(url, 'id_del_country', destination)
                    url = add_or_replace_parameter(url, 'packagecount', '1')
                    url = add_or_replace_parameter(url, 'length[1]', '10')
                    url = add_or_replace_parameter(url, 'width[1]', '10')
                    url = add_or_replace_parameter(url, 'height[1]', '10')
                    url = add_or_replace_parameter(url, 'weight[1]', str(weight))
                    data_quotes.append({'url':url, 'destination': destination, 'weight': weight})

        meta = {}
        meta['data_quotes'] = data_quotes[1:]
        meta['destination'] = data_quotes[0]['destination']
        meta['weight'] = data_quotes[0]['weight']

        url = data_quotes[0]['url']

        code = response.xpath('//input[@name="code"]/@value').extract()[0]
        url = add_or_replace_parameter(url, 'code', code)
        yield Request(url, callback=self.parse_products, meta=meta)

    def parse_products(self, response):

        products = response.xpath('//tr[@class="courier-results"]')
        for product in products:
            name = ' '.join(product.xpath('.//td[3]//text()').extract()).strip()
            if name:
                loader = ProductLoader(Product(), selector=product)
                weight = response.meta['weight']
                identifier = name + '-' + str(weight) + '-'+response.meta['destination']
                name = name
                loader.add_value('name', name + ' ' + response.meta['destination'])
                loader.add_value('identifier', identifier)
                loader.add_value('sku', str(weight))
                price = product.xpath(u'.//td[contains(text(), "£")]//text()').extract()
                loader.add_value('price', price)
                loader.add_value('url', "http://www.interparcel.com")
                loader.add_value('image_url', '')
                loader.add_value('brand', extract_brand(name))
                loader.add_value('category', response.meta['destination'])
                item = loader.load_item()
                yield item

        data_quotes = response.meta.get('data_quotes', None)
        if data_quotes:
            meta = response.meta
            yield Request('http://www.interparcel.com', dont_filter=True, callback=self.parse_code, meta=response.meta)

    def parse_code(self, response):
        data_quotes = response.meta.get('data_quotes', None)

        meta = {'data_quotes': data_quotes[1:],
                'destination': data_quotes[0]['destination'],
                'weight': data_quotes[0]['weight']}

        url = data_quotes[0]['url']

        code = response.xpath('//input[@name="code"]/@value').extract()[0]
        url = add_or_replace_parameter(url, 'code', code)
        yield Request(url, callback=self.parse_products, meta=meta)
