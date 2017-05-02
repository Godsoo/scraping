import csv
import os

import re
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
import datetime


def normalize_space(s):
    ''' Cleans up space/newline characters '''
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

HERE = os.path.abspath(os.path.dirname(__file__))

class NaturalcomplexionsSpider(ProductCacheSpider):
    name = 'naturalcomplexions.co.uk'
    allowed_domains = ['naturalcomplexions.co.uk']
    start_urls = ['http://www.naturalcomplexions.co.uk/brands']

    def _start_requests(self):
        yield Request('http://www.skinfantastic.co.uk/Agera/', callback=self.parse_cat)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[@id="left-nav"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url) + '?limit=all', callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//li[@class="item"]'):
            product = Product()
# List and actual product prices differ
#            try:
#                product['price'] = extract_price(productxs.select('.//p[@class="special-price"]/span[@class="price"]//text()').re(r'[\d.,]+')[0])
#            except:
#                product['price'] = extract_price(productxs.select('.//span[@class="price"]//text()').re(r'[\d.,]+')[0])
            request = Request(urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="product-name"]/@href').extract()[0]), callback=self.parse_product, meta=response.meta)
            yield self.fetch_product(request, self.add_shipping_cost(product))
        
        for page in hxs.select('//div[@class="categorylisting"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page) + '?limit=all', callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        price = hxs.select('//p[@class="special-price"]/span[@class="price"]//text()').extract() or hxs.select('//div[@class="product-shop-info"]//span[@class="regular-price"]/span[@class="price"]//text()').extract()

        loader = ProductLoader(item=response.meta.get('product', Product()), selector=hxs)

        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_xpath('sku', '//p[@class="sku"]/span/text()')
        loader.add_value('name', normalize_space(' '.join(hxs.select('//div[@class="product-name"]/h1/text()').extract())))
        loader.add_value('price', price.pop())
        loader.add_xpath('category', '//div[@class="breadcrumbs"]/ul/li[position()>1 and position()<last()]/a/text()')
        img = hxs.select('//p[@class="product-image"]//img/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_xpath('brand', '//div[@class="breadcrumbs"]/ul/li[3]/a/text()')

        if not loader.get_output_value('category'):
            loader.add_xpath('category', '//div[@class="product-category-title"]/text()')
        if not loader.get_output_value('brand'):
            loader.add_xpath('brand', '//div[@class="product-category-title"]/text()')

        if hxs.select('//p[@class="availability in-stock"]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        return item
