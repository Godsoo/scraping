# -*- coding: utf-8 -*-
import json
from time import time
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class CanadiantireSpider(scrapy.Spider):
    name = "legocanada-canadiantire.ca"
    allowed_domains = ["canadiantire.ca", "sp10050e31.guided.ss-omtrdc.net"]
    start_urls = ["http://sp10050e31.guided.ss-omtrdc.net/?site=ct;format=json;count=36;q=lego"]    

    def parse(self, response):
        data = json.loads(response.body)
        next_p = data['pagination'].get('next', None)
        if next_p:
            yield scrapy.Request(response.urljoin(next_p))

        base_products_url = 'http://www.canadiantire.ca/ESB/PriceAvailability?Banner=CTR&isKiosk=FALSE&Language=E&_=%s&Product=' %int(time()*1000)
        prod_ids = []
        for result in data['results']:
            prod_ids.append(result['field']['prod-id'])
        url = base_products_url + ','.join(prod_ids)
        yield scrapy.Request("http://www.canadiantire.ca",
                             callback=self.get_cookies,
                             dont_filter=True,
                             meta={'products': data['results'],
                                   'url': url,
                                   'cookiejar': 'url'})
    
    def get_cookies(self, response):
        yield scrapy.Request(response.meta['url'],
                      self.parse_products,
                      meta=response.meta)

    @staticmethod
    def parse_products(response):
        price_data = json.loads(response.body)
        products = response.meta['products']
        for product in products:
            loader = ProductLoader(response=response, item=Product())

            loader.add_value('name', product['field']['prod-name'])
            loader.add_value('url', response.urljoin(product['field']['pdp-url']))
            loader.add_value('image_url', response.urljoin(product['field']['thumb-img-url']))
            loader.add_value('category', 'Lego')
            loader.add_value('brand', 'Lego')
            loader.add_value('identifier', product['field']['prod-id'])
            loader.add_value('sku', product['field']['sku-number'])
            for p in price_data:
                if p['Product'] == product['field']['prod-id']:
                    loader.add_value('price', p['Price'])
                    break
            if loader.get_output_value('price')<=0:
                loader.add_value('stock', 0)
            yield loader.load_item()
