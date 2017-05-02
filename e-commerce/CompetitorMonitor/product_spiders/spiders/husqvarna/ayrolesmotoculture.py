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

class AyrolesMotocultureSpider(ProductCacheSpider):
    name = 'ayrolesmotoculture.fr'
    allowed_domains = ['ayroles-motoculture.com']
    start_urls = ['http://www.ayroles-motoculture.com/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[contains(@class, "categories")]//a/@href').extract():
            yield Request(url, callback=self.parse)

        for productxs in hxs.select('//table[@class="productListing"]/tr[@class="boxTexts"]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//span[@class="TextPrixAccListing"]//text()').re(r'[\d.,]+')))
            product['sku'] = ''.join(productxs.select('.//td[3]/text()[1]').extract()).strip()
            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="textenom"]/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))

        for url in hxs.select('//a[contains(@title, " Page ")]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        loader.add_value('url', response.url)
        loader.add_value('stock', '1')
        loader.add_value('identifier', response.url.split('-')[-1].split('.')[0])
        loader.add_xpath('name', '//span[@class="textenom"]/text()')
        loader.add_xpath('category', '(//font[@class="bg_list_tt"]/text())[1]')
        img = hxs.select('//a[@class="highslide"]/@href').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('brand', response.meta.get('brand'))

        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        return item
