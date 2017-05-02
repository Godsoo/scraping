import os
import json
import re

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from utils import extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ActiveSportsNutritionSpider(BaseSpider):
    name = 'usn-activesportsnutrition.co.uk'
    allowed_domains = ['activesportsnutrition.co.uk']
    start_urls = ['http://www.activesportsnutrition.co.uk']

    def start_requests(self):
        brands = {'USN': ['http://www.activesportsnutrition.co.uk/brand/usn'],
                  'Optimum Nutrition': ['http://www.activesportsnutrition.co.uk/brand/Optimum-Nutrition'],
                  'BSN': ['http://www.activesportsnutrition.co.uk/brand/BSN'],
                  'PhD': ['http://www.activesportsnutrition.co.uk/brand/PhD', 'http://www.activesportsnutrition.co.uk/brand/phd-woman'],
                  'Maxi Nutrition': ['http://www.activesportsnutrition.co.uk/brand/Maxi-Nutrition'],
                  'Reflex': ['http://www.activesportsnutrition.co.uk/brand/Reflex-Nutrition'],
                  'Mutant': ['http://www.activesportsnutrition.co.uk/brand/Mutant'],
                  'Cellucor': ['http://www.activesportsnutrition.co.uk/brand/cellucor'],
                  'Sci-MX': ['http://www.activesportsnutrition.co.uk/brand/Sci-Mx-Nutrition']}

        for brand, urls in brands.iteritems():
            for url in urls:
                yield Request(url, meta={'brand': brand}, callback=self.parse_brand)

    def parse_brand(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[contains(@class, "category-group")]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), meta=response.meta)
            
    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//article[@class="product"]//a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product.replace('all-products/', '')), callback=self.parse_product, meta=response.meta)

        pages = hxs.select('//div[@class="productpaging"]//a/@href').extract()
        for page in pages:
            page_url = urljoin_rfc(get_base_url(response), page)
            yield Request(page_url, callback=self.parse, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand', ''))
        categories = hxs.select('//div[contains(@class, "breadcrumbs")]//a/text()').extract()
        loader.add_value('category', categories)

        identifier = hxs.select('//input[@name="UCII_recordId"]/@value').extract()
        if not identifier:
            log.msg('PRODUCT WHIOUT IDENTIFIER: ' + response.url)
            return
 
        loader.add_value('identifier', identifier[0])

        sku = identifier
        loader.add_value('sku', sku)

        image_url = hxs.select('//meta[@itemprop="image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

        price = ''.join(hxs.select('//*[@itemprop="price"]//text()').extract())
        loader.add_value('price', price)

        #in_stock =  hxs.select('//p[@class="availability in-stock"]')
        #if not in_stock:
        #    loader.add_value('stock', '0')

        if loader.get_output_value('price') <= 19.99:
            loader.add_value('shipping_cost', 4.99)

        item = loader.load_item()


        options = hxs.select('//select/option[@value!=""]')
        if options:
            for option in options:
                option_item = Product(item)
                value = option.select('@value').extract()[0].replace('&', '&amp;')
                option_item['identifier'] += '-' + hxs.select('//ul[@class="product-select"]/script/text()').re("optionCheckArray_1\['%s'\]\['isOption'\]='(.+?)';" %value)[0]
                option_item['name'] += ' ' + option.select('text()').extract()[0].strip()
                yield option_item
        else:
            yield item
