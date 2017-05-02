import csv
import os

import re
import demjson
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
import datetime


HERE = os.path.abspath(os.path.dirname(__file__))

class AtlanticMotocultureSpider(ProductCacheSpider):
    name = 'atlanticmotoculture.fr'
    allowed_domains = ['atlanticmotoculture.fr']
    start_urls = ['http://www.atlanticmotoculture.fr/index.php']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[contains(@class, "sf-menu")]//a/@href').extract():
            yield Request(url, callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//ul[@id="product_list"]/li'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//span[@class="price"]//text()').re(r'[\d.,]+')))
            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="product_img_link"]/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        for url in hxs.select('//ul[contains(@class, "pagination")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        loader.add_value('url', response.url)
        loader.add_value('stock', '1')
        loader.add_xpath('identifier', '//input[@id="product_page_product_id"]/@value')
        loader.add_xpath('sku', '//p[@id="product_reference"]/span/text()')
        loader.add_xpath('name', '//div[@id="primary_block"]//h1/text()')
        loader.add_xpath('category', '//div[@class="breadcrumb"]/a[2]//text()')
        img = hxs.select('//img[@id="bigpic"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', response.meta.get('brand'))

        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        return item
