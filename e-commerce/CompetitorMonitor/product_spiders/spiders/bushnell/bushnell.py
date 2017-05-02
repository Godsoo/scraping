import re
import csv
import os
import copy
import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup

HERE = os.path.abspath(os.path.dirname(__file__))


class BushnellSpider(BaseSpider):
    name = 'bushnell-bushnell.com'
    allowed_domains = ['bushnell.com', 'shopbushnell.com']
    start_urls = ('http://www.bushnell.com',)

    def start_requests(self):
        with open(os.path.join(HERE, 'bushnell_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request('http://www.shopbushnell.com/detail/BSN+' + row['SKU'], meta={'product': row}, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta.get('product')
        loader = ProductLoader(Product(), response=response, selector=hxs)
        loader.add_value('name', product['Product Description'].encode('utf-8'))
        loader.add_value('url', response.url)
        loader.add_value('category', product['Class'])
        loader.add_value('brand', 'Bushnell')
        loader.add_value('identifier', product['SKU'])
        loader.add_value('sku', product['SKU'])
        image_url = hxs.select('//div[@id="prod_image"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))
        price = hxs.select('//div[@id="prod_price"]/text()')
        price = price[0].extract() if price else '0.00'
        loader.add_value('price', '')
        yield loader.load_item()
