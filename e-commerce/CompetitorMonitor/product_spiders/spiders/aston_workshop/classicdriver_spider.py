import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class ClassicDriverSpider(BaseSpider):
    name = 'astonworkshop-classicdriver.com'
    allowed_domains = ['classicdriver.com']
    start_urls = ['https://www.classicdriver.com/en/api/search/cars?year_from=1930&year_to=1995&make=110&nit=99999&currency=GBP']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        product_url = 'https://www.classicdriver.com/en/node/'

        products = json.loads(response.body)['items']
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('name', product['title'])
            loader.add_value('url', product_url+str(product['nid']))
            loader.add_value('identifier', product['nid'])
            loader.add_value('price', product['price'][0].get('amount', 0))
            yield loader.load_item()
