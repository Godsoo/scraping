"""
Second spec: https://www.assembla.com/spaces/competitormonitor/tickets/4948-e-bedding-%7C-argos-%7C-new-site
This spider is set to extract all items from the Bedding category.
"""
import re
import os
import csv
import urllib
from urlparse import urljoin as urljoin_rfc

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy import log
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class EBeddingArgosSpider(BaseSpider):
    name = 'ebedding-argos.co.uk'
    allowed_domains = ['argos.co.uk']
    start_urls = ['http://www.argos.co.uk/static/Browse/ID72/37924427/c_1/1|category_root|Home+and+garden|33005908/c_2/2|cat_33005908|Bedding|37924427.htm']

    def parse(self, response):
        subcategories = response.xpath('//ul[@id="categoryList"]/li/a/@href').extract()
        for url in subcategories:
            url = response.urljoin(url.replace('/c_1', '/s/Price%3A+Low+-+High/pp/150/c_1'))
            yield Request(url,
                          callback=self.parse_listing)

    def parse_listing(self, response):

        next_page = response.xpath('//div[contains(@class,"pagination")]//a[text()="Next"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]),
                          callback=self.parse_listing)

        products = response.xpath('//dt[@class="title"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url),
                          callback=self.parse_product)

    def parse_product(self, response):
        options = response.xpath('//ul[@class="swatch-carousel-items"]//a/@href').extract()
        for url in options:
            yield Request(response.urljoin(url),
                          callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)

        # name
        name = response.xpath('//h1[@class="product-name-main"]/*[@itemprop="name"]/text()').extract()
        name = name[0].strip()
        loader.add_value('name', name)

        # price
        price = response.xpath(
            '//div[contains(@class, "product-price-wrap")]/div[@itemprop="price"]/@content').extract()
        price = extract_price("".join(price).strip())
        loader.add_value('price', price)

        identifier = response.url.split('/')[-1].split('.')[0]
        loader.add_value('identifier', identifier)

        # sku
        sku = response.xpath("//li//text()[contains(., 'EAN')]").re('EAN: (.*)\.')
        if sku:
            sku = sku[0].split(":")[-1].split('.')[0].strip()
            loader.add_value('sku', sku)
        else:
            loader.add_value('sku', identifier)


        # category
        categories = response.xpath('//ol[contains(@class, "breadcrumb")]//a/span/text()').extract()[-3:]
        for category in categories:
            loader.add_value('category', category)

        # product image
        image_url = response.xpath('//meta[@property="og:image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        # url
        loader.add_value('url', response.url)
        # brand
        loader.add_xpath('brand', '//span[@class="product-name-brand"]/a[@itemprop="brand"]/text()')

        yield loader.load_item()

