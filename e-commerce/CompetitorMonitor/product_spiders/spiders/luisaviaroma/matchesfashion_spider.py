import os
import re
import json
import csv
import urlparse

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class MatchesfashionSpider(BaseSpider):
    name = 'matchesfashion.com'
    allowed_domains = ['matchesfashion.com']
    start_urls = ('http://www.matchesfashion.com',)

    categories = ['http://www.matchesfashion.com/womens/giuseppe-zanotti']

    def start_requests(self):
        params = {'Currency': 'EUR',
                  'DisplayCurrency': '',
                  'Shipping': 'ARE'}

        req = FormRequest(url="http://www.matchesfashion.com/settings", formdata=params)
        yield req

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        
        with open(os.path.join(HERE, 'luisaviaroma.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Matches Fashion']!='NO MATCHES':
                    meta = {}
                    meta['category'] = row['Category']
                    meta['brand'] = row['Brand']
                    meta['sku'] = row['Codes']
                    meta['url'] = row['Matches Fashion']

                    yield Request(row['Matches Fashion'], callback=self.parse_product, meta=meta)

        for category in self.categories:
            yield Request(category, callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[contains(@class, "product medium")]/a[contains(@href, "product")]/@href').extract()
        for product in products:
            category = hxs.select('//h3[@class="name"]/text()').extract()[0]
            url = urljoin_rfc(base_url, product)
            yield Request(url, callback=self.parse_product, meta={'category': category})

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta
  
        l = ProductLoader(item=Product(), response=response)
        l.add_xpath('identifier', '//input[@id="AddToBasketMain"]/@data-event-label')
        brand = hxs.select('//div[@class="info"]/h2[@class="designer"]/a/text()').extract()[0]
        name = hxs.select('//div[@class="info"]/h3[@class="description"]/text()').extract()[0].strip()
        l.add_value('name', brand + ' ' + name)

        brand = meta.get('brand') if meta.get('brand', None) else brand
        l.add_value('brand', brand)

        url = meta.get('url') if meta.get('url', None) else response.url
        l.add_value('url', url)

        sku = meta.get('sku') if meta.get('sku', None) else hxs.select('//div[@class="buy"]//select[@id="ProductItemId"]/@data-wpc').extract()[0]
        l.add_value('sku', sku)

        image_url = hxs.select('//a[@class="zoom"]/img[@class="product-image" and contains(@src, "_1_")]/@src').extract()
        if image_url:
            l.add_value('image_url', image_url[0])
        l.add_value('category', meta.get('category'))
        
        price = hxs.select('//div[@class="details"]//div[@class="pricing"]/div[@class="price"]/span[@class="sale"]/text()').extract()
        if price:
            price = price[0]
        else:
            price = hxs.select('//div[@class="details"]//div[@class="pricing"]/div[@class="price"]/text()').extract()
            if price:
                price = price[0]
            else:
                price = 0
        l.add_value('price', price)
        yield l.load_item()
