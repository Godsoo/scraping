import os
import json
import re
import time

from scrapy import Spider
from scrapy.http import Request
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
    name = 'legousa-jet.com'
    allowed_domains = ['jet.com']
    start_urls = ('https://jet.com/search?term=lego',)
    _re_sku = re.compile('(\d\d\d\d\d?)')

    search_url = 'https://jet.com/api/search/'
    product_url = 'https://jet.com/product/product/%(product_id)s'

    download_delay = 5
    rotate_agent = True
    handle_httpstatus_list = [500, 501, 502, 503, 504, 400, 408, 403, 456, 429, 302]

    @retry_decorator
    def parse(self, response):
        data = {'term': 'lego'}
        token = response.xpath('//*[@data-id="csrf"]/@data-val').extract()[0][1:-1]  # [1:-1] removes quotation marks "..."
        ssid = response.xpath('//*[@data-id="session_id"]/@data-val').extract()[0][1:-1]
        headers = {'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'X-CSRF-Token': token,
                   'Content-Type': 'application/json',
                   'Host': 'jet.com',
                   'X-Requested-With': 'XMLHttpRequest'}
        cookies={'s_cc': 'true',
                 '__ssid': ssid}

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
            req = Request(self.search_url,
                          dont_filter=True,
                          method='POST',
                          body=json.dumps(formdata),
                          callback=self.parse_products,
                          headers=headers,
                          cookies=cookies,
                          meta={'cookies': cookies, 'headers': headers, 'data': formdata,
                                'dont_redirect': True, 'page': next_page})
            yield req

        # Collect products
        for product in data['result']['products']:
            identifier = product['id']
            name = product['title']
            url = self.product_url % {'product_id': identifier}
            sku = self._re_sku.findall(name)
            sku = sku[0] if sku else ''
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
            loader.add_value('sku', sku)
            loader.add_value('brand', brand)
            loader.add_value('category', brand)
            loader.add_value('price', str(price))
            if shipping_cost > 0:
                loader.add_value('shipping_cost', str(shipping_cost))
            loader.add_value('image_url', image)
            yield loader.load_item()

    def proxy_service_check_response(self, response):
        return response.status in self.handle_httpstatus_list
