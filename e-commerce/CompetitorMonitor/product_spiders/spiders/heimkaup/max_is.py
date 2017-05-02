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

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from heimkaupitems import HeimkaupProduct as Product

HERE = os.path.abspath(os.path.dirname(__file__))

class MaxIsSpider(BaseSpider):
    name = 'heimkaup-max.is'
    allowed_domains = ['max.is']

    start_urls = ['http://max.is']

    def __init__(self, *args, **kwargs):
        super(MaxIsSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        categories = hxs.select('//div[@class="categories"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        next_page = hxs.select('//a[@class="next ajaxLoadpage"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//div[@class="product-item"]//a/@href').extract()
        for url in set(products):
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select('//div[@class="info"]/h2[@class="header"]/text()').extract()
        brand = product_name[0]
        product_name = u' '.join(product_name)
        product_price = hxs.select('//div[@class="pricebg"]/span[@class="price"]/text()')[0].extract()
        product_code = sku = hxs.select('//span[@class="productNr"]/text()').extract()
        image_url = hxs.select('//a[contains(@class, "mainimage")]/img/@src').extract()
        category = hxs.select('//li[@class="active"]/a/text()').extract()
        category = category[0] if category else ''
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', sku)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_value('category', category)
        product_price = extract_price(product_price.replace('.', '').replace(',', '.'))
        loader.add_value('price', product_price)
        out_of_stock = hxs.select('//div[@class="lagerp lagerp3"]/text()').extract()
        out_of_stock = True if (out_of_stock and out_of_stock[0] == u'S\xe9rp\xf6ntun') else False
        if out_of_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
