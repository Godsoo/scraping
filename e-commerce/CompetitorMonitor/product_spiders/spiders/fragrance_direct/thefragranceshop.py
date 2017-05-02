import os
import re
import json
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from fragrancedirectitem import FragranceDirectMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class TheFragranceShopSpider(BaseSpider):
    name = 'fragrancedirect-thefragranceshop.co.uk'
    allowed_domains = ['thefragranceshop.co.uk']

    start_urls = ['http://www.thefragranceshop.co.uk/default.aspx']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="nav-menu"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brands = hxs.select('//li[contains(@class, "brandsLogo")]/a/@href').extract()
        brands += hxs.select('//ul[contains(@class, "sub-brand")]//a[not(contains(@href, "#"))]/@href').extract()
        for url in brands:
            yield Request(url, callback=self.parse_products)

        sub_cats = hxs.select('//ul[contains(@class, "submanuflist")]//a/@href').extract()
        for url in sub_cats:
            yield Request(url, callback=self.parse_products)

        products = None
        data = re.findall("searchInit\((.*)\)' ", response.body)
        if data:
            data = json.loads(data[0])
            criteria = data['searchResult']['criteria']
            products = data['searchResult']['products']
        else:
            try:
                data = json.loads(response.body)
                criteria = data['criteria']
                products = data['products']
            except:
                products = None
                
        if products:
            for product in products:
                url = '/products/' + product['seName'] +'-'+ str(product['id']) + '.aspx'
                url = urljoin_rfc(base_url, url)
                yield Request(url, callback=self.parse_product)

            ajax_url = 'http://www.thefragranceshop.co.uk/api/search/'
            criteria['currentPage'] += 1
            yield Request(ajax_url, method='POST', 
                          dont_filter=True, body=json.dumps(criteria), 
                          headers={'Content-Type': 'application/json; charset=utf-8'},
                          callback=self.parse_products)

        products = hxs.select('//ul[@class="product-grid"]/li/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        brand = hxs.select('//h1/text()').extract()
        brand = brand[0].strip() if len(brand)>1 else ''

        product_price = hxs.select('//span[@class="price price-large"]/text()').extract()
        if not product_price:
            product_price = hxs.select('//div[contains(@class, "premium-product-detail")]/div/h3/text()').extract()
        product_price = extract_price(product_price[0])

        product_code = re.findall('Stock Code: (.*)', response.body)
        if not product_code:
            product_code = re.findall('-(\d+).aspx',response.url)

        product_code = product_code[0].strip()

        image_url = hxs.select('//div[contains(@class, "product-image")]//img[contains(@class, "img-responsive")]/@src').extract()
        if not image_url:
            image_url = hxs.select('//img[contains(@class, " img-lg")]/@src').extract()

        image_url = image_url[0] if image_url else ''

        categories = hxs.select('//ol[contains(@class, "breadcrumb")]/li/a/text()').extract()
        if categories:
            categories = categories[1:]

        product_name = hxs.select('//div[@property="gr:name"]/@content').extract()[0]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        loader.add_value('image_url', image_url)
        for category in categories:
            if category.upper() != 'BRANDS':
                loader.add_value('category', category)
        loader.add_value('price', product_price)
        out_of_stock = hxs.select('//div[@ng-controller="productCtrl"]//div[@class="in-stock"]//span/text()').re('not In stock')
        if out_of_stock:
            loader.add_value('stock', 0)

        product = loader.load_item()
        metadata = FragranceDirectMeta()
        if product.get('price'):
            metadata['price_exc_vat'] = Decimal(product['price']) / Decimal('1.2')
        product['metadata'] = metadata

        yield product
