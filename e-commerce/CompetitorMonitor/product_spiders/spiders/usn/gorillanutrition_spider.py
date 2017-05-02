import os
import json
import re
from copy import deepcopy

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from utils import extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class GorillaNutritionSpider(BaseSpider):
    name = 'usn-gorillanutrition.co.uk'
    allowed_domains = ['gorillanutrition.co.uk']
    start_urls = ['http://gorillanutrition.co.uk']

    def start_requests(self):
        brands = {'USN': ['USN'],
                  'Optimum Nutrition': ['Optimum Nutrition'],
                  'BSN': ['BSN'], 
                  'PhD': ['PHD Nutrition', 'PHD Woman'],
                  'Maxi Nutrition': ['Maxi Nutrition'], 
                  'Reflex': ['Reflex Nutrition'], 
                  'Mutant': ['Mutant'], 
                  'Cellucor': ['Cellucor'], 
                  'Sci-MX': ['Sci-MX']}

        search_url = 'http://gorillanutrition.co.uk/index.php?route=product/search&search=%s'
        for brand, brand_queries in brands.items():
            for brand_query in brand_queries:
                yield Request(search_url % brand_query, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="product-list"]//div[@class="name"]/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta=response.meta)

        next = hxs.select('//a[text()=">"]/@href').extract()
        if next:
            next = urljoin_rfc(get_base_url(response), next[0])
            yield Request(next, callback=self.parse, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@id="content"]/h1/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand', ''))
        loader.add_value('category', response.meta.get('brand', ''))

        identifier = hxs.select('//input[@name="product_id"]/@value').extract()
        if not identifier:
            log.msg('PRODUCT WHIOUT IDENTIFIER: ' + response.url)
            return

        sku = re.findall('Product Code:  (.*) ', ' '.join(hxs.select('//div[@class="description"]//text()').extract()))
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier[0])
        image_url = hxs.select('//img[@id="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        price = hxs.select('//div[@class="product-info"]//div[@class="price"]/span[@class="price-new"]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="price"]/text()').re('Price: (.*)')
        loader.add_value('price', price)

        in_stock = 'IN STOCK' in ''.join(hxs.select('//div[@class="description"]//text()').extract()).upper()
        if not in_stock:
            loader.add_value('stock', '0')
 
        if loader.get_output_value('price') < 60:
            loader.add_value('shipping_cost', 1.99)

        item = loader.load_item()

        options = hxs.select('//select[contains(@name, "option")]/option[@value!=""]')
        if options:
            for option in options:
                option_item = deepcopy(item)
                option_item['identifier'] += '-' + option.select('@value').extract()[0]
                option_item['name'] += ' ' + option.select('text()').extract()[0]
                yield option_item
        else:
            yield item
