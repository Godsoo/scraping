# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoader
from scrapy.selector import HtmlXPathSelector
from product_spiders.utils import extract_price
import json


class NikeSpider(BaseSpider):
    name = u'nike.com'
    allowed_domains = ['store.nike.com']
    start_urls = [
        'http://store.nike.com/gb/en_gb/pw/shoes/brkZ1js?sortOrder=viewAll|asc',
    ]

    download_delay = 20

    def parse(self, response):
        ajax_url = 'http://store.nike.com/html-services/gridwallData?country=GB&lang_locale=en_GB&gridwallPath=shoes/brkZ1js&pn=1&sortOrder=viewAll|asc'
        yield Request(ajax_url, callback=self.parse_shoes)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product = response.meta['product']
        price = extract_price(''.join(hxs.select('//*[@itemprop="price"]/text()').extract()))
        product['price'] = price
        if price < 50:
            product['shipping_cost'] = 4.50
        else:
            product['shipping_cost'] = 0
        yield product

    def parse_shoes(self, response):
        data = json.loads(response.body)
        if 'nextPageDataService' in data:
            yield Request(data['nextPageDataService'], callback=self.parse_shoes)
        for product in data['sections'][0]['products']:
            if not product['nikeid']:
                colorways = product.get('colorways', [product]) or [product]
                for product_color in colorways:
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('url', product_color['pdpUrl'])
                    loader.add_value('name', product['title'])
                    loader.add_value('image_url', product['spriteSheet'])
                    try:
                        price = extract_price(product.get('localPrice', '').replace(u'\xa3', ''))
                    except:
                        price = 0
                    loader.add_value('price', price)
                    identifier = product_color['pdpUrl'].partition('pid-')[2].split('/')[0]
                    loader.add_value('identifier', identifier)
                    sku = product['spriteSheet'].partition('img0=')[2].split('_')[0]
                    loader.add_value('sku', sku)
                    loader.add_value('brand', 'Nike')
                    if price < 50:
                        loader.add_value('shipping_cost', 4.50)
                    else:
                        loader.add_value('shipping_cost', 0)

                    if price == 0:
                        yield Request(product_color['pdpUrl'], callback=self.parse_product, meta={'product':loader.load_item()})
                    else:
                        yield loader.load_item()
    
