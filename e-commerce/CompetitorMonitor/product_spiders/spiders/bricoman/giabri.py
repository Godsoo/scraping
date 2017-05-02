import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from pricecheck import valid_price

HERE = os.path.abspath(os.path.dirname(__file__))

class GiabriSpider(BaseSpider):
    name = 'bricoman-giabri.it'
    allowed_domains = ['giabri.it']

    def start_requests(self):
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['bricoman_code']
                yield Request('http://giabri.it/default.asp?cmdString=%s&cmdOP=AND&cmd=searchProd&bFormSearch=1&orderBy=priceA&pg=1' % row['model'].replace(' ', '+'),
                                  meta={'sku': sku, 'model': row['model'], 'price': row['price']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        search_results = []
        products = hxs.select(u'//div[@class="resultBox"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            url = product.select(u'./h2/a/@href')[0].extract()
            url = urljoin_rfc(get_base_url(response), url)
            loader.add_value('url', url)
            name = product.select(u'./h2/a/text()')[0].extract().strip()
            loader.add_value('name', name)
            loader.add_value('sku', response.meta['sku'])
            loader.add_value('identifier', response.meta['sku'])
            price = product.select(u'./ul/li[@class="price"]/h3[@class="mainPrice"]/text()')[0].extract().replace(',', '.')
            loader.add_value('price', price)
            if valid_price(response.meta['price'], loader.get_output_value('price')):
                search_results.append(loader)
            search_results.sort(key=lambda x: x.get_output_value('price'))

        search_q = response.meta['model'].lower().split(' ')
        for result in search_results:
            name = result.get_output_value('name')
            if all([x in name.lower() for x in search_q]):
                yield result.load_item()
                return

        if search_results:
            yield search_results[0].load_item()
