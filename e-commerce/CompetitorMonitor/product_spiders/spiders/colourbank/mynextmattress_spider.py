import os
import re
import csv
import json
import urlparse
from copy import deepcopy
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class MyNextMattressSpider(BaseSpider):
    name = 'mynextmattress.co.uk'
    allowed_domains = ['mynextmattress.co.uk']
    start_urls = ('https://www.mynextmattress.co.uk',)
    retry_times = 3
    download_delay = 5
    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:37.0) Gecko/20100101 Firefox/37.0'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        categories = hxs.select('//ul[@id="nav"]/li/a[contains(@class, "level")]/@href').extract()
        categories += hxs.select('//div[@class="catBox"]//a/@href').extract()
        categories += hxs.select('//h3[@class="brandName"]/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category.replace('http:', 'https:')))
 
        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for product in products:
            categories = hxs.select('//div[@class="breadcrumbs"]/ul/li//text()').extract()
            categories = ''.join(categories).split('/')
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product, meta={'categories': categories[1:]})

        next_page = hxs.select('//a[contains(@class, "next")]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(base_url, next_page[-1])
            yield Request(next_page.replace('http:', 'https:'))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brands = hxs.select('//a[contains(@href, "brands/")]/span/text()').extract()
        

        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('sku', '//input[@name="product"]/@value')
        loader.add_value('category', '')
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')

        brand = ''
        for b in brands:
            if b.upper().strip() in loader.get_output_value('name').upper():
                brand = b
                break

        loader.add_value('brand', brand)
        img = hxs.select('//ul[@id="product-page-slider"]//img/@src').extract()
        img = urljoin_rfc(base_url, img[0]) if img else ''
        loader.add_value('image_url', img)
        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        item = loader.load_item()

        if not item.get('identifier', None):
            log.msg('Product without identifier, URL: ' + response.url)
            return

        data = re.search('Product.Config\((.*)\);', response.body)
        if data:
            data = data.groups()[0]
            data = json.loads(data)
            product_options = {}
            for attr in data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        product_options[product] = ' - '.join((product_options.get(product, ''), option['label']))

            for option_id, option_name in product_options.iteritems():
                option_item = deepcopy(item)
                try:
                    option_item['price'] = extract_price(data['childProducts'][option_id]['finalPrice'])
                except:
                    option_item['price'] = extract_price(data['childProducts'][option_id]['price'])

                option_item['name'] = option_item['name'] + ' ' + option_name
                option_item['identifier'] = option_item['identifier'] + '-' + option_id
                yield option_item
                
        
        else:
            item['price'] = extract_price(''.join(hxs.select('//form//p[@class="special-price"]//span[@class="price"]/text()').extract()))
            if not item['price']:
                item['price'] = extract_price(''.join(hxs.select('//div[@class="product-right"]//span[@class="price"]/text()').extract()))
            yield item

