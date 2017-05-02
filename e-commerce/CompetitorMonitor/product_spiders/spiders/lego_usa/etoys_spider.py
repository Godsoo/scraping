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

from scrapy.shell import inspect_response

HERE = os.path.abspath(os.path.dirname(__file__))


class EtoysSpider(BaseSpider):
    name = 'legousa-etoys.com'
    allowed_domains = ['etoys.com']
    start_urls = ('http://www.etoys.com/category/index.jsp?categoryId=11813492', 'http://www.etoys.com/search/index.jsp?categoryId=4034303&f=PAD%2FBrand+Name+Secondary%2FLEGO&fbc=1&fbn=Brand+Name+Secondary|LEGO',)
    _re_sku = re.compile('(\d\d\d\d\d?)')

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'etoys_map_deviation.csv')

    def parse(self, response):
        #yield Request('http://www.etoys.com/product/index.jsp?productId=17356076', callback=self.parse_product)
        #return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="module_Taxonomy1"]/p/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category + '&view=all'))

        # next = hxs.select('//a[span[@id="resultsNxtBtn"]]/@href').extract()
        # if next:
        #    yield Request(urljoin_rfc(base_url, next[-1]), callback=self.parse_lego)

        products = hxs.select('//ol[@id="products"]/li/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        identifier = hxs.select('//input[@name="productId"]/@value').extract()
        if identifier:
            yield Request(response.url, dont_filter=True, callback=self.parse_product)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return

        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        identifier = hxs.select('//input[@name="productId"]/@value').extract()[0]

        name = hxs.select('//div[@id="product-detail"]/div/h1/text()').extract()[0]

        sku = self._re_sku.findall(name)
        sku = sku[0] if sku else ''

        category = hxs.select('//a[@class="breadcrumb"]/text()').extract()[-1]
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_xpath('brand', '//label[@class="makerStyle"]/text()')
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        stock = 1
        price = hxs.select('//div[@id="price-ours"]/strong/span/text()').extract()[0]
        # price = price[0] if price else ''
        loader.add_value('price', price)
        tmp = hxs.select('//div[@id="config"]//div[@id="status" and @class="out"]')
        if tmp:
            stock = 0
        loader.add_value('stock', stock)
        loader.add_xpath('image_url', '//img[@id="mainProductImage"]/@src')
        yield loader.load_item()
