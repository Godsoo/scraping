import os
import re
import json
import csv
import urlparse

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from heimkaupitems import HeimkaupProduct as Product

HERE = os.path.abspath(os.path.dirname(__file__))

class EymundssonSpider(BaseSpider):
    name = 'heimkaup-eymundsson.is'
    allowed_domains = ['eymundsson.is']

    start_urls = ['http://eymundsson.is']

    def __init__(self, *args, **kwargs):
        super(EymundssonSpider, self).__init__(*args, **kwargs)

    def sort_url(self, url):
        if not 'orderby' in url:
            url += ('?' if '?' not in url else '&') + 'orderby=title&orderdesc=false'
        return url

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        categories = hxs.select('//div[@id="nav"]//li[contains(@class,"level2")]/a/@href').extract()
        for url in categories:
            url = self.sort_url(urljoin_rfc(base_url, url))
            yield Request(url)

        subcategories = hxs.select('//div[@id="subnav"]//li/a/@href').extract()
        for url in subcategories:
            url = self.sort_url(urljoin_rfc(base_url, url))
            yield Request(url)

        next_page = hxs.select('//a[@id="nextpage" and not(contains(@class,"unactive"))]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//div[@class="info"]/h2/a/@href').extract()
        for url in set(products):
            product_id = url.split('=')[1]
            url = 'http://www.eymundsson.is/nanar/?productid={}'.format(product_id)
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select('//h1/span[@class="title"]/text()')[0].extract()
        product_price = hxs.select('//div[@class="price"]/span/p/strong/text()').re('([\d\.]+) kr.')[0]
        product_code = sku = hxs.select('//div[@class="moreItem"]/span[@class="title" and contains(text(),"mer:")]/following-sibling::span/text()').extract()
        image_url = hxs.select('//a[@class="jqzoom"]/img/@src').extract()
        category = hxs.select('//div[@class="moreItem"]/span[@class="title" and text()="Form:"]/following-sibling::span/text()').extract()
        category = category[0] if category else ''
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', sku)
        loader.add_value('identifier', product_code)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_value('category', category)
        product_price = extract_price(product_price.replace('.', '').replace(',', '.'))
        loader.add_value('price', product_price)
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)

        yield loader.load_item()
