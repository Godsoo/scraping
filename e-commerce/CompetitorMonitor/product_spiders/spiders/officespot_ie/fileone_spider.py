import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class FileOneSpider(BaseSpider):
    name = 'fileone.ie'
    allowed_domains = ['fileone.ie']
    start_urls = ('http://www.fileone.ie',)

    def __init__(self, *args, **kwargs):
        super(FileOneSpider, self).__init__(*args, **kwargs)
        self.skus = {}
        with open(os.path.join(HERE, 'skus.csv'), 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                self.skus[row[2].lower()] = row[0].lower()

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="top-categories"]//li[div]/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        sub_categories = hxs.select('//div[@class="subcategories"]/a/@href').extract()
        for sub_category in sub_categories:
            yield Request(urljoin_rfc(base_url, sub_category))

        next = hxs.select('//a[@class="right-arrow"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]))

        products = hxs.select('//table[contains(@class, "products")]//div[@class="details"]/a/@href').extract()

        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@class="title-print"]/text()')
        loader.add_value('url', response.url)
        identifier = hxs.select('//input[@name="productid"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        external_sku = hxs.select('//td[@id="product_code"]/text()').extract()
        if external_sku:
            external_sku = external_sku[0].lower().strip()
            sku = self.skus.get(external_sku)
            loader.add_value('sku', sku or external_sku)

        loader.add_xpath('price', '//span[@id="product_price"]/text()')
        loader.add_xpath('image_url', '//img[@id="product_thumbnail"]/@src')
        loader.add_xpath('category', '//a[@class="bread-crumb last-bread-crumb"]/text()')
        loader.add_xpath('brand', '//div[@class="manufacturer-info"]/a/img/@alt')
        stock = hxs.select('//td[@class="property-value product-quantity-text"]/text()').extract()[0].split('item')[0].strip()
        loader.add_value('stock', stock)
        yield loader.load_item()
