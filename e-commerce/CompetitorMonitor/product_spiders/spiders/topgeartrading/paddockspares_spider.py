import re
import os
import csv
import json
import copy
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoader

from product_spiders.utils import extract_price


HERE = os.path.abspath(os.path.dirname(__file__))


class PaddockSparesSpider(BaseSpider):
    name = 'paddockspares.com'
    allowed_domains = ['paddockspares.com']
    start_urls = ('http://www.paddockspares.com/land-rover-wheels-and-tyres/bf-goodrich-tyres.html',
                  'http://www.paddockspares.com/land-rover-wheels-and-tyres/general-tyres.html',
                  'http://www.paddockspares.com/land-rover-wheels-and-tyres/cooper-tyres.html',
                  'http://www.paddockspares.com/land-rover-wheels-and-tyres/insa-turbo-tyres.html',
                  'http://www.paddockspares.com/land-rover-wheels-and-tyres/enduro-tyres.html',
                  'http://www.paddockspares.com/land-rover-wheels-and-tyres/gt-radial-tyres.html',
                  'http://www.paddockspares.com/land-rover-wheels-and-tyres/maxxis-tyres.html',
                  'http://www.paddockspares.com/land-rover-wheels-and-tyres/yokohama-tyres.html',
                  'http://www.paddockspares.com/land-rover-wheels-and-tyres/kumho-tyres.html')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        sub_categories = hxs.select('//div[@class="sub_cat_name"]/h2/a/@href').extract()
        for sub_cateogry in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_cateogry)
            yield Request(url)

        products = hxs.select('//ol[@id="products-list"]/li[contains(@class, "item")]/div/div[@class="product-name"]//p/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        name = hxs.select('//div[@class="product-name"]/h2/text()').extract()[0].split(' - ')[-1]
        loader.add_value('name', name.replace(' Tyre Only', '').replace(' TYRE ONLY', ''))

        loader.add_xpath('brand', '//tr[th/text()="Brand"]/td/text()')
        loader.add_xpath('category', '//tr[th/text()="Brand"]/td/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('sku', '//tr[th/text()="Part Number"]/td/text()')

        image_url = hxs.select('//td/a/img/@src').extract()
        image_url = image_url[0] if image_url else ''

        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url))

        identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        loader.add_value('identifier', identifier)

        price = hxs.select('//div[@class="product-shop"]//div[@class="price-box"]/span[@class="price-including-tax"]/span[@class="price"]/text()').extract()
        '''
        if not price:
            price = ''.join(hxs.select('//td/p[span/text()="PRICE:"]/text()').extract()).strip()
        '''
        if price:
            loader.add_value('price', price[0])
        else:
            loader.add_value('price', 0)
            loader.add_value('stock', 0)
        yield loader.load_item()


