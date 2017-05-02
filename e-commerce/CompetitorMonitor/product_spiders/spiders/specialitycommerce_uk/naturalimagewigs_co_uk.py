import os
import csv

from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class NaturalimagewigsCoUk(BaseSpider):
    name = 'specialitycommerceuk-naturalimagewigs.co.uk'
    allowed_domains = ['naturalimagewigs.co.uk']
    start_urls = ['http://www.naturalimagewigs.co.uk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@id="megadrop"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        sub_categories = hxs.select('//span[@class="subcategories"]//a/@href').extract()
        for sub_category in sub_categories:
            yield Request(urljoin_rfc(base_url, sub_category))

        products = hxs.select('//table[contains(@class, "products-table")]//td[contains(@class, "product-cell")]/div[@class="image"]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next = hxs.select('//a[@class="right-arrow"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        #brand = hxs.select('//span[@itemprop="brand"]/text()').extract()
        brand = ''#brand[0] if brand else ''

        product_name = hxs.select('//div[@id="center-main-content"]/h1/text()').extract()
        product_name = product_name[0].strip()
       
        product_price = hxs.select('//span[@id="product_price"]/text()').extract()
        product_price = extract_price(product_price[0])

        product_code = hxs.select('//input[@name="productid"]/@value').extract()[0]

        image_url = hxs.select('//img[@id="product_thumbnail"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        
        #categories = hxs.select('//div[@id="breadcrumb"]/p/span/a//text()').extract()
        categories = []#categories[1:] if categories else ''
        
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

        loader.add_value('price', product_price)
        if loader.get_output_value('price')<=0:
            loader.add_value('stock', 0)

        item = loader.load_item()
        options = hxs.select('//select[contains(@name, "colour_select") or contains(@name, "product_options")]/option[not(@value="") and text()]')
        if options:
            option_item = deepcopy(item)
            for option in options:
                option_id = option.select('@value').extract()[0]
                option_item['identifier'] = product_code + '-' + option_id
                image_url = hxs.select('//img[contains(@src, "id='+option_id+'")]/@src').extract()
                option_item['image_url'] = urljoin_rfc(base_url, image_url[0]) if image_url else ''
                option_item['name'] = product_name + ' ' + option.select('text()').extract()[0]
                option_item['sku'] = option_item['identifier']
                yield option_item
        else:
            yield item
