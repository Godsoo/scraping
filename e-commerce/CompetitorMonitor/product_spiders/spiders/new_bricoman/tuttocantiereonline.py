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

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class TuttoCantiereOnlineSpider(BaseSpider):
    name = 'newbricoman-tuttocantiereonline.com'
    allowed_domains = ['tuttocantiereonline.com']
    start_urls = ('http://www.tuttocantiereonline.com',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@id="theMenu_acc"]//a[@class="left main-cate"]')
        for cat in categories:
            category = cat.select('./text()').extract()
            if category:
                category = category[0].strip()

            url = cat.select('./@href')[0].extract()
            subcategories = cat.select('./..//a/@href').extract()
            subcategories += url
            for u in subcategories:
                yield Request(urljoin_rfc(get_base_url(response), u), callback=self.parse_category, meta={'category': category})

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//h2[@class="product-name"]/a')
        for prod in products:
            url = prod.select('./@href')[0].extract()
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        main_name = hxs.select('//div[@class="product-name"]/h1/text()')[0].extract()
        main_identifier = hxs.select('//input[@name="product"]/@value')[0].extract()
        main_price = hxs.select('//span[@id="product-price-%s"]//text()' % main_identifier)
        if main_price:
            main_price = extract_price(''.join(main_price.extract()).replace('.', '').replace(',', '.'))
        image_url = hxs.select('//div[@class="MagicToolboxWrapper"]/a/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//div[@class="MagicToolboxContainer"]/img/@src').extract()
        if image_url:
            image_url = image_url[0]
        else:
            image_url = ''
        in_stock = hxs.select('//div[@class="MagicToolboxWrapper"]/a/img/@src') is not None
        category = response.meta.get('category')

        main_sku = hxs.select('//div[@class="product-name"]/span/text()')[0].extract()
        main_sku = main_sku.replace('COD.: SKU', '').replace('COD.: ', '')
        sub_products = []#hxs.select('//div[@id="product-options-wrapper"]//option')

        if not sub_products:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('name', main_name)
            loader.add_value('identifier', main_identifier)
            if main_price:
                loader.add_value('price', main_price)
            else:
                log.msg('ERROR: No price url: ' + response.url)
                return
                #loader.add_value('price', 0)

            
            loader.add_value('image_url', image_url)
            loader.add_value('url', response.url)
            if not in_stock:
                loader.add_value('stock', 0)
            if category:
                loader.add_value('category', category)
            loader.add_value('sku', main_sku)
            yield loader.load_item()
