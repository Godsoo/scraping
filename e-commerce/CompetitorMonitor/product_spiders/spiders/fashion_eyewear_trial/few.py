# -*- coding: utf-8 -*-

import os
import re
import csv
import json
from StringIO import StringIO
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price

from scrapy import log

from product_spiders.items import ProductLoader, Product


HERE = os.path.abspath(os.path.dirname(__file__))

class fewSpider(BaseSpider):
    name = "fashioneyewear-trial-fashioneyewear.co.uk"
    allowed_domains = ["www.fashioneyewear.co.uk"]

    filename = os.path.join(HERE, 'fashioneyeware_products.csv')
    start_urls = ('file://' + filename,)
    
    def parse(self, response):
        rows = csv.DictReader(StringIO(response.body))
        for row in rows:
            if 'fashioneyewear' in row['Link']:
                yield Request(row['Link'].strip(), dont_filter=True, callback=self.parse_product, meta={'row':row})
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)  
        base_url = get_base_url(response)

        row = response.meta['row']
        name = row['Title'].decode('utf8')
        brand = hxs.select('//tr[td/text()="Brand"]/td/text()').extract()[-1]

        l = ProductLoader(item=Product(), response=response)
        l.add_value('name', name)
        l.add_value('sku', row['SKU'])
        l.add_value('identifier', row['SKU'])
        l.add_value('url', response.url)
        l.add_value('brand', brand)
        l.add_value('category', brand)
        image_url = hxs.select('//div[@class="product-image"]/img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        l.add_value('image_url', image_url)
        price = hxs.select('//p[@class="special-price"]/span[@class="price"]/text()').extract()
        if not price:
            price = hxs.select('//span[@class="regular-price"]/span[@class="price"]/text()').extract()
        price = price[0] if price else 0

        l.add_value('price', price)
        if not l.get_output_value('price'):
            l.add_value('stock', 0)

        item = l.load_item()

        options_config = re.search(r'var spConfig=new Product.Config\((.*)\)', response.body)
        if options_config:
            option_item = deepcopy(item)
            # Load price html from options
            prices_config = re.search(r'confData=new AmConfigurableData\((.*)\);confData.', response.body)
            prices_data = json.loads(prices_config.group(1))

            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                if 'SIZE' in attr['label'].upper():
                    continue 
                for option in attr['options']:
                    for product in option['products']:
                        if row['Colour'].upper().strip() in option['label'].upper().strip():
                            products[product] = ' - '.join((products.get(product, ''), option['label']))
                            html = ''
                            for i, data in prices_data.iteritems():
                                if option['id'] in i:
                                    prices_hxs = HtmlXPathSelector(text=data['price_clone_html'])
                                    break
                            price = prices_hxs.select('//p[@class="special-price"]/span[@class="price"]/text()').extract()
                            if not price:
                                price = prices_hxs.select('//*[@class="regular-price"]/span[@class="price"]/text()').extract()
                            prices[product] = extract_price(price[0])

            for option_id, option_name in products.iteritems():
                option_item = deepcopy(item)
                option_item['price'] = prices[option_id]
                if not option_item['price']:
                    option_item['stock'] = 0
                image_page = 'http://www.fashioneyewear.co.uk/amconf/media/index/id/%s'
                yield Request(image_page % option_id, callback=self.parse_image, meta={'item': option_item})
        else:
            yield item

    def parse_image(self, response):
        hxs = HtmlXPathSelector(response)  
        base_url = get_base_url(response)

        item = response.meta['item']
        
        image_url = hxs.select('//img/@src').extract()
        item['image_url'] = urljoin_rfc(base_url, image_url[0]) if image_url and len(image_url[0])<255 else '' if image_url else ''
        yield item
