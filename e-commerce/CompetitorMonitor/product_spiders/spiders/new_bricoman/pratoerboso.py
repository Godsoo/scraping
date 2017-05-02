import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class PratoErbosoSpider(BaseSpider):
    name = 'newbricoman-pratoerboso.org'
    allowed_domains = ['pratoerboso.org']
    start_urls = ('http://www.pratoerboso.org',)
    download_delay = 0

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//a[@class="link_categoria"]/@href').extract()
        categories += hxs.select('//a[@class="pageResults"]/@href').extract()
        for cat in categories:
            yield Request(cat)

        for product in self.parse_products(hxs, response):
            yield product

    def parse_products(self, hxs, response):
        products = hxs.select('//table[@class="infoBoxContents"]/tr')
        base_url = get_base_url(response)
        for p in products:
            url = p.select('.//td/a/span/../@href').extract()
            if not url:
                continue

            url = url[0]
            loader = ProductLoader(item=Product(), selector=p)
            loader.add_xpath('name', './/td/a/span/text()')
            loader.add_value('url', urljoin_rfc(base_url, url))
            brand = p.select('.//td/a/text()').extract()
            if brand:
                brand = brand[0]
                loader.add_value('brand', brand)
            category = hxs.select('//span[@class="categoria_menu_selezionata"]/text()').extract()[0]
            loader.add_value('category', category)
            image_url = p.select('.//td/a/img/@src').extract()[0]
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))
            price = p.select('.//span[@class="productSpecialPrice"]/text()')
            if not price:
                price = p.select('.//td/span/font/b/text()')
            if not price:
                price = p.select('.//span[@id="productPrice"]/text()')
            price = price.extract()[0]
            price = price.replace('.', '').replace(',', '.')
            loader.add_value('price', price)
            identifier = url.split('id=')[-1]
            loader.add_value('identifier', identifier)
            yield Request(url, callback=self.parse_product, meta={'loader': loader})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = response.meta.get('loader')
        sku = hxs.select('//span[@class="modelText"]/text()').extract()
        if sku:
            sku = sku[0].strip().split('MODELLO: ')[-1]
        else:
            sku = ''

        loader.add_value('sku', sku)
        yield loader.load_item()
