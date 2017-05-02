from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price_eu
from scrapy.http import Request, FormRequest
from urlparse import urljoin
import re, json


class BilkaDkSpider(BaseSpider):

    name = 'bilka.dk'
    allowed_domains = ['bilka.dk']
    start_urls = ('https://www.bilka.dk/search?q=lego',)

    def parse(self, response):

        yield Request(
            url='https://www.bilka.dk/s%C3%B8g/json?q=lego',
            callback=self.parse_results
        )


    def parse_results(self, response):

        total_results = json.loads(response.body)['numberOfResults']
        total_pages = int(total_results) / 12 + 1

        for page in range(1, total_pages):
            yield Request(
                url='https://www.bilka.dk/s%C3%B8g/json?q=lego%3Arelevance&page={}'.format(page),
                callback=self.parse_page,
                dont_filter=True
            )


    def parse_page(self, response):

        products = json.loads(response.body)['tiles']

        for product in products:

            item = {}
            item['identifier'] = product['code']
            item['name'] = product['title']
            item['price'] = product['price']['value']
            item['image_url'] = 'https://www.bilka.dk' + product['image']['url']
            item['url'] = 'https://www.bilka.dk' + product['url']

            if int(item['price']) < 2500:
                item['shipping_cost'] = 39

            yield Request(item['url'], meta={'item': item}, callback=self.parse_product)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        item = response.meta['item']

	product_loader = ProductLoader(item=Product(), selector=hxs)

	product_loader.add_value('identifier', item['identifier'])
	product_loader.add_value('image_url', item['image_url'])
	product_loader.add_value('name', item['name'])
	product_loader.add_value('url', response.url)
	product_loader.add_value('shipping_cost', item['shipping_cost'])
	product_loader.add_value('price', item['price'])

        sku = ''
	for match in re.finditer(r"([\d,\.]+)", item['name']):
	    if len(match.group()) > len(sku):
		sku = match.group()

        if sku:
            product_loader.add_value('sku', sku)
        else:
            product_loader.add_value('sku', item['identifier'])

        stock = 1 if 'data-stock-status=inStock' in response.body else 0
	product_loader.add_value('stock', stock)

	yield product_loader.load_item()
