from decimal import Decimal
import os
import re
import json
import csv
import urlparse

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

from fragrancedirectitem import FragranceDirectMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class SuperdrugSpider(BaseSpider):
    name = 'fragrancedirect-superdrug.com'
    allowed_domains = ['superdrug.com']

    start_urls = ['http://www.superdrug.com']

    brands = []

    def start_requests(self):
        yield Request('http://www.superdrug.com/brands/a-to-z', callback=self.parse_brands)

    
    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        self.brands = hxs.select('//li[@class="brandcat"]/a/span/text()').extract()

        for start_url in self.start_urls:
            yield Request(start_url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//nav[contains(@class, "navbar")]/div/ul/li/a[not(@title="Brands")]/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))
        
        sub_categories = hxs.select('//div[@class="subnav-wrapper"]//a/@href').extract()
        sub_categories += hxs.select('//div[@class="catlevel"]//li[contains(@class, "roll")]/a/@href').extract()
        for sub_category in sub_categories:
            yield Request(urljoin_rfc(base_url, sub_category))

        all_products = hxs.select('//a[@class="viewrange"]/@href').extract()
        if all_products:
            yield Request(urljoin_rfc(base_url, all_products[0]))

        products = hxs.select('//a[@class="name"]/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next = hxs.select('//li[contains(@class, "next")]/a/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        colour_options = response.xpath('//ul[contains(@class, "colour-palette")]//a/@href').extract()
        for colour_option in colour_options:
            yield Request(urljoin_rfc(base_url, colour_option), callback=self.parse_product)

        product_name = response.xpath('//h2[contains(@class, "lead")]/text()').extract()
        product_name = product_name[0]

        product_brand = ''
        for brand in self.brands:
            if brand.upper() in product_name.upper():
                product_brand = brand
                break
       
        product_price = response.xpath('//div[contains(@class, "pricing")]/span/text()').extract()
        product_price = extract_price(product_price[0]) if product_price else '0'
       
        product_code = response.xpath('//input[@name="productID"]/@value').extract()[0]

        image_url = response.xpath('//div[@class="zoomTile"]/img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        
        categories = hxs.select('//div[contains(@class, "breadcrumb")]/a[not(@href="/") and not(@class="active")]/text()').extract()[:-1]
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', product_brand)
        loader.add_value('image_url', image_url)
        loader.add_value('category', categories)
        out_of_stock = hxs.select('//form[contains(@class, "add_to_notification")]')
        if out_of_stock:
            loader.add_value('stock', 0)

        if loader.get_output_value('price')>=10:
            loader.add_value('shipping_cost', 0)
        else:
            loader.add_value('shipping_cost', 3)

        loader.add_value('price', product_price + loader.get_output_value('shipping_cost'))

        promotional_data = hxs.select('//div[contains(@class, "promotion")]/a/text()').extract()
        promotional_data += [''.join(hxs.select('//span[contains(@class, "was")]//text()').extract())]

        item = loader.load_item()
        metadata = FragranceDirectMeta()
        metadata['promotion'] = ', '.join(promotional_data)
        if item.get('price'):
            metadata['price_exc_vat'] = Decimal(item['price']) / Decimal('1.2')
        item['metadata'] = metadata
        yield item
