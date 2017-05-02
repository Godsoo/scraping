# -*- coding: utf-8 -*-

import csv
import os
import json
import time
import paramiko

from scrapy import Spider, Request
from product_spiders.utils import excel_to_csv
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


def retry_decorator(callback):
    def new_callback(obj, response):
        if response.status in obj.handle_httpstatus_list:
            time.sleep(180)
            r = response.request.replace(dont_filter=True)
            r.meta['recache'] = True
            yield r
        else:
            res = callback(obj, response)
            if res:
                for r in res:
                    yield r
    return new_callback


class JetSpider(Spider):
    name = 'householdessentials-jet.com'
    allowed_domains = ['jet.com']
    start_urls = ['https://jet.com']

    filename = os.path.join(HERE, 'householdessentials_products.csv')

    search_url = 'https://jet.com/api/search/'
    product_url = 'https://jet.com/product/product/%(product_id)s'

    products = {}

    rotate_agent = True
    handle_httpstatus_list = [500, 501, 502, 503, 504, 400, 408, 403, 456, 429, 302]


    def start_requests(self):
        if not os.path.exists(self.filename):
            transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
            password = "n4pyn8vU"
            username = "household"
            transport.connect(username = username, password = password)
            sftp = paramiko.SFTPClient.from_transport(transport)
            files = sftp.listdir_attr()
            last = get_last_file(files)
            if last.filename.endswith('.xlsx'):
                sftp.get(last.filename, 'household_products.xlsx')
                excel_to_csv('household_products.xlsx', self.filename)
            else:
                sftp.get(last.filename, self.filename)
            if last.filename != 'householdessentials_products.csv':
                sftp.put(self.filename, 'householdessentials_products.csv')

        with open(self.filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.products[row['Amazon ASIN'].upper()] = row['Item Number']

        yield Request(self.start_urls[0])


    @retry_decorator
    def parse(self, response):
        token = response.xpath('//*[@data-id="csrf"]/@data-val').extract()[0][1:-1]  # [1:-1] removes quotation marks "..."
        ssid = response.xpath('//*[@data-id="session_id"]/@data-val').extract()[0][1:-1]
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'X-CSRF-Token': token,
                   'Content-Type': 'application/json',
                   'Host': 'jet.com',
                   'X-Requested-With': 'XMLHttpRequest'}
        cookies={'s_cc': 'true',
                 '__ssid': ssid}
        brands = ['CEDARFRESH', 'CEDAR FRESH', 'EKO', 'HOUSEHOLD ESSENTIALS', 'KROSNO', 'LEIFHEIT', 'SOEHNLE', 'BURDA']
        for brand in brands:
            data = {'term': brand, 'category': '0'}
            req = Request(self.search_url,
                          dont_filter=True,
                          method='POST',
                          body=json.dumps(data),
                          callback=self.parse_products,
                          headers=headers,
                          cookies=cookies,
                          meta={'cookies': cookies, 'headers': headers, 'data': data,
                                'dont_redirect': True})
            yield req

            data = {'term': brand, 'attribute': 'Brands~%s' % brand.title(), 'category': '0'}
            req = Request(self.search_url,
                          dont_filter=True,
                          method='POST',
                          body=json.dumps(data),
                          callback=self.parse_products,
                          headers=headers,
                          cookies=cookies,
                          meta={'cookies': cookies, 'headers': headers, 'data': data, 'dont_redirect':True})
            yield req

        for upc, item_number in self.products.iteritems():
            data = {'term': upc}
            req = Request(self.search_url,
                          dont_filter=True,
                          method='POST',
                          body=json.dumps(data),
                          callback=self.parse_products,
                          headers=headers,
                          cookies=cookies,
                          meta={'cookies': cookies, 'headers': headers, 'data': data, 'dont_redirect':True,
                                'upc_search': True, 'sku': item_number})
            yield req

    @retry_decorator
    def parse_products(self, response):
        data = json.loads(response.body)
        total = int(data['result']['total'])
        from_ = int(data['result']['query']['from'])
        size = int(data['result']['query']['size'])
        limit = from_ + size

        if limit < total:
            # Get next page
            next_page = int(response.meta.get('page', 1)) + 1
            cookies = response.meta['cookies']
            headers = response.meta['headers']
            formdata = response.meta['data']
            formdata['page'] = next_page
            meta = response.meta.copy()
            meta['page'] = next_page
            req = Request(self.search_url,
                          dont_filter=True,
                          method='POST',
                          body=json.dumps(formdata),
                          callback=self.parse_products,
                          headers=headers,
                          cookies=cookies,
                          meta=meta)
            yield req

        # Collect products
        for product in data['result']['products']:
            sku_found = ''

            asin_group = product.get('asin')
            if not asin_group:
                continue
            asin_group = set(map(unicode.upper, asin_group))
            for asin in asin_group:
                if asin in self.products:
                    sku_found = self.products[asin]
                    break
            if not sku_found:
                continue

            identifier = product['id']
            name = product['title']
            option_name = ' '.join([v['value'] for v in product['variants'] if 'ONE SIZE' not in v['value'].upper()])
            if option_name:
                name += ' ' + option_name
            url = self.product_url % {'product_id': identifier}
            brand = product['manufacturer']
            image = product['image']['raw']
            price = product['productPrice']['referencePrice']
            shipping_cost = 0
            if price < 35:
                shipping_cost = 5.99

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', identifier)
            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_value('sku', sku_found)
            loader.add_value('brand', brand)
            loader.add_value('category', brand)
            loader.add_value('price', str(price))
            if shipping_cost > 0:
                loader.add_value('shipping_cost', str(shipping_cost))
            loader.add_value('image_url', image)
            yield loader.load_item()

    def proxy_service_check_response(self, response):
        return response.status in self.handle_httpstatus_list

def get_last_file(files):
    exts = ('xlsx', '.csv')
    last = None
    for f in files:
        if ((last == None and f.filename[-4:] in exts) or
            (f.filename[-4:] in exts and
             f.st_mtime > last.st_mtime)):
            last = f
    return last
