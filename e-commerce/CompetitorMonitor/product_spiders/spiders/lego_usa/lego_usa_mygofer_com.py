import datetime
from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import json

payload = '{"filters":{},"brandFilter":null,"sellersFilter":null,"catgroupId":null,"levelOne":null,"searchMode":"KEYWORD_SEARCH","sortBy":"RECOMMENDED","keyword":"lego","pageNum":%%pagenum%%,"rowCount":999,"ffmMode":"ALL","priceFilter":null,"hideOOS":true,"uNo":"3413","session":{"guid":0,"emailId":"","sessionKey":null,"userId":366026,"appId":"MYGOFER"},"security":{"src":"web","ts":"%%ts%%","authToken":""}}'


class MygoferSpider(BaseSpider):
    name = 'lego_usa_mygofer_com'
    allowed_domains = ['mygofer.com']
    start_urls = ('https://www.mygofer.com/lps-mygofer/api/v1/mygofer/cis/autoLoginUserAsGuest',)

    def parse(self, response):
        pagenum = response.meta.get('page', 1)
        next_page = False
        if pagenum > 1:
            data = json.loads(response.body)
            if data['payload']['numFound'] == 999:
                next_page = True
        if pagenum == 1 or next_page:
            body = payload.replace('%%pagenum%%', str(pagenum)).replace('%%ts%%', datetime.datetime.now().isoformat())
            yield Request('https://www.mygofer.com/lps-mygofer/api/v1/mygofer/search',
                          method='POST',
                          headers={'Content-Type': 'application/json'},
                          body=body,
                          meta={'page': pagenum + 1})
        if pagenum > 1:
            # parse products
            for product in data['payload']['products']:
                if 'prdType' not in product:
                    continue
                if product['prdType'] == 'NONVARIATION':
                    product_loader = ProductLoader(item=Product(), response=response)
                    product_loader.add_value('name', product['name'])
                    product_loader.add_value('identifier', product['partNumber'])
                    product_loader.add_value('url', 'http://www.mygofer.com/p/p-' + product['partNumber'])
                    product_loader.add_value('price', product['salePrice'])
                    product_loader.add_value('sku', product.get('mfpartno'))
                    product_loader.add_value('dealer', product['soldBy'])
                    product_loader.add_value('brand', 'LEGO')
                    if product['shipStock'] != '1':
                        product_loader.add_value('stock', 0)
                    if product['img']:
                        product_loader.add_value('image_url', product['img'])
                    prod = product_loader.load_item()
                    yield prod
                else:
                    body = '{"partNumber":"%%partnum%%","session":{"guid":0,"emailId":"","sessionKey":null,"userId":366026,"appId":"MYGOFER"},"security":{"src":"web","ts":"%%ts%%","authToken":""}}'
                    body = body.replace('%%partnum%%', product['itemPartNumber']).replace('%%ts%%',
                                                                                          datetime.datetime.now().isoformat())
                    yield Request('https://www.mygofer.com/lps-mygofer/api/v1/mygofer/product/view#' + product['itemPartNumber'],
                                  method='POST',
                                  headers={'Content-Type': 'application/json'},
                                  body=body,
                                  callback=self.parse_options,
                                  meta={'dont_retry': True})

    def parse_options(self, response):
        data = json.loads(response.body)
        name = data['payload']['product']['name']
        identifier = data['payload']['product']['partNumber']
        dealer = data['payload']['product']['soldBy']
        sku = data['payload']['product']['modelNo']
        for product in data['payload']['product']['childAttributeInfo']:
            product_loader = ProductLoader(item=Product(), response=response)
            opt_id = product.pop('PARTNUMBER', '')
            opt_stock = product.pop('INSTOCK', '')
            del(product['WEBSTATUS'])
            opt_img = product.pop('IMAGEURL', '')
            p_name = name
            for option_value in product.itervalues():
                p_name += ' ' + option_value
            product_loader.add_value('name', p_name)
            product_loader.add_value('identifier', identifier + '_' + opt_id)
            product_loader.add_value('url', 'http://www.mygofer.com/p/p-' + identifier)
            product_loader.add_value('sku', sku)
            product_loader.add_value('dealer', dealer)
            product_loader.add_value('brand', 'LEGO')
            if opt_stock != '1':
                product_loader.add_value('stock', 0)
            if opt_img:
                product_loader.add_value('image_url', opt_img)
            prod = product_loader.load_item()
            body = '{"parentPartNo":"%%partnum%%","uNo":"3413","session":{"guid":0,"emailId":"","sessionKey":null,"userId":366026,"appId":"MYGOFER"},"security":{"src":"web","ts":"%%ts%%","authToken":""}}'
            body = body.replace('%%partnum%%', identifier).replace('%%ts%%',datetime.datetime.now().isoformat())
            yield Request('https://www.mygofer.com/lps-mygofer/api/v1/mygofer/product/getPrice',
                          method='POST',
                          headers={'Content-Type': 'application/json'},
                          body=body,
                          meta={'prod': prod, 'opt_id': opt_id},
                          callback=self.parse_price)

    @staticmethod
    def parse_price(response):
        data = json.loads(response.body)
        prod = response.meta['prod']
        opt_id = response.meta['opt_id']
        prod['price'] = data['payload']['priceMap'][opt_id]['salePrice']
        yield prod
