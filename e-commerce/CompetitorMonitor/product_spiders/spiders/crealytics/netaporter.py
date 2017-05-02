from decimal import Decimal
import os
import re

from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class NetAPorterSpider(BaseSpider):
    name = 'crealytics-net-a-porter.com'
    allowed_domains = ['net-a-porter.com']
    start_urls = ('https://www.net-a-porter.com/gb/en/Shop/Designers/Adidas_Originals',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Gucci',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Givenchy',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Alexander_McQueen',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Chloe',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Diane_von_Furstenberg',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Valentino',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Burberry_Prorsum',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Burberry_London',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Burberry_Brit',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Rag_and_bone',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/KENZO',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Stella_McCartney',
                  'https://www.net-a-porter.com/gb/en/Shop/Designers/Burberry_Beauty')

    def start_requests(self):
        params = {'channel': 'INTL',
                  'country': 'GB',
                  'httpsRedirect': '',
                  'language': 'en',
                  'redirect': ''}

        req = FormRequest(url="http://www.net-a-porter.com/intl/changecountry.nap?overlay=true",
                          formdata=params,
                          callback=self.parse_country)
        yield req

    def parse_country(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        products = response.xpath('//div[@class="description"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        for url in response.xpath('//div[@class="pagination-links"]//a/@href').extract():
            yield Request(response.urljoin(url))

    def parse_product(self, response):
        colors = response.xpath('//div[@class="product-swatch current style-scope nap-product-swatch"]/a/@href').extract()
        for url in colors:
            yield Request(response.urljoin(url), callback=self.parse_product)

        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//h2[@class="product-name"]/text()').extract()[0].strip()
        l.add_value('name', name)
        l.add_value('url', response.url)
        sku = response.xpath('//div[@class="product-code"]/span/text()').extract()
        sku = sku[0] if sku else ''
        l.add_value('sku', sku)
        l.add_value('identifier', sku)
        image_url = response.xpath('//img[contains(@class,"product-image")]/@src').extract()
        if image_url:
            l.add_value('image_url', response.urljoin(image_url[0]))
        category = response.xpath('//a[@class="designer-name"]/span/text()').extract()
        l.add_value('category', category)
        l.add_value('brand', category)
        price = response.xpath('//meta[@class="product-data"]/@data-price').extract()
        if price:
            price = extract_price(price[0]) / Decimal('100')
        else:
            price = 0
        l.add_value('price', price)
        if price <= Decimal('349'):
            l.add_value('shipping_cost', '5.00')
        yield l.load_item()
