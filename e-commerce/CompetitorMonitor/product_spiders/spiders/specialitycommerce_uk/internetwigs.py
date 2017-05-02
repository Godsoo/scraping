import os
import re
import json
import csv
import urlparse
from decimal import Decimal

from copy import deepcopy

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class InternetWigsSpider(BaseSpider):
    name = 'specialitycommerceuk-internetwigs.com'
    allowed_domains = ['internetwigs.com']

    start_urls = ['http://www.internetwigs.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="mega_menu"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)

        #sub_categories = hxs.select('//table[tr/td/img[contains(@src, "by-type")]]//div[@class="menu"]//a/@href').extract()
        #for sub_category in sub_categories:
            #yield Request(urljoin_rfc(base_url, sub_category))

    def parse_category(self, response):
        products = response.xpath('//div[@id="product_list_inner"]//span[@class="prti"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//a[@title="Next page"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]), callback=self.parse_category)
        
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

	try:
	    variant_price = re.search('variants\[.*?Array\(.*?selling_price.*?pound;(.*?)<\\\/b.*?\)', response.body).group(1)
	    log.msg('[{}] First variant price: {}'.format(response.url, variant_price))
            variant_price = Decimal(variant_price)
        except:
            variant_price = Decimal(0)

        loader = ProductLoader(item=Product(), response=response)
        brand = hxs.select('//span[@itemprop="brand"]/text()').extract()
        brand = brand[0] if brand else ''

        product_name = hxs.select('//span[@itemprop="name"]/text()').extract()
        product_name = product_name[0].strip()
       
        product_price = hxs.select('//form[@name="details"]//td[@id="product_details"]//font[@class="selling_price"]/b/text()').extract()
        product_price = extract_price(product_price[0])
        if product_price != variant_price:
            log.msg('[{}] Prices mismatch: {} <-> {} '.format(response.url, variant_price, product_price))
       
        product_code = hxs.select('//input[@name="pid"]/@value').extract()[0]

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        
        categories = hxs.select('//div[@id="breadcrumb"]/p/span/a//text()').extract()
        categories = categories[1:] if categories else ''
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))

        for category in categories:
            loader.add_value('category', category)

        if variant_price and variant_price != Decimal(0):
            loader.add_value('price', variant_price)
        else:
            loader.add_value('price', product_price)
        if loader.get_output_value('price')<=0:
            loader.add_value('stock', 0)

        item = loader.load_item()
        options = hxs.select('//select[contains(@class, "selectfield")]/option[not(@value="NULL_")]')
        if options:
            option_item = deepcopy(item)
            for option in options:
                option_item['identifier'] = product_code + '-' + option.select('@value').extract()[0]
                option_item['name'] = product_name + ' ' + option.select('text()').extract()[0]
                option_item['sku'] = option_item['identifier']
                yield option_item
        else:
            yield item
