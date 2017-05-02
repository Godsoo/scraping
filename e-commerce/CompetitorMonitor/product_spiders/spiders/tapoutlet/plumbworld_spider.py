import re
import os
import csv
import hashlib
import re
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
from product_spiders.items import Product, ProductLoaderWithNameStrip\
                             as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class PlumbworldSpider(BaseSpider):

    name = 'plumbworld.co.uk'
    allowed_domains = ['plumbworld.co.uk']
    start_urls = ('http://www.plumbworld.co.uk',)

    download_delay = 0.1

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@id="L"]/div[@id="Secondary"]/div/ul/li/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        sub_categories = hxs.select('//div[@class="groupBox3"]/a[1]/@href').extract()
        sub_categories += hxs.select('//div[@class="groupBox2"]/a[1]/@href').extract()
        for sub_category in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_category)
            yield Request(url)

        products = hxs.select('//div[@class="listingProduct"]/div[@class="listingData"]/a[text()!=""]/@href').extract()
        products += hxs.select('//table[@class="searchGrid"]/tr/td/p/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        pagination = hxs.select('//div[@class="Pagination"]/ul/li/a/@href').extract()
        for page in pagination:
            url = urljoin_rfc(get_base_url(response), page)
            yield Request(url)


        products = hxs.select('//div[contains(@class, "itemBOM")]')
        if products:
            category = hxs.select('//div[@id="Breadcrumb"]/div/a/text()').extract()[-1]
            for product in products:
                sku = product.select('div//span[@itemprop="sku"]/text()').extract()

                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('image_url', 'div/a/img/@src')
                loader.add_value('category', category)
                loader.add_xpath('brand', '//div[@class="productBox" and p/text()="Manufacturer"]/a/img/@alt')
                loader.add_value('url', response.url)
                loader.add_xpath('name', 'div/p[@itemprop="name"]/text()')
                loader.add_xpath('identifier', 'div//input[@class="PQ"]/@id')
                if sku:
                    loader.add_value('sku', sku[0].replace(' ', ''))
                price = product.select('div/table/tr/td[@class="bigPrice"]/text()').extract()
                if price:
                    price = price[0]
                else:
                    price = '0.0'
                loader.add_value('price', price)
                in_stock = 'IN STOCK' in ''.join(product.select('div/p[@class="productStockBOM"]/text()').extract()).upper()
                if not in_stock:
                    loader.add_value('stock', 0)
                yield loader.load_item()
        identifier = hxs.select('//div[@id="Product"]/div/form/table/tr/td/input[@name="PID"]/@value').extract()
        if not identifier:
            identifier = hxs.select('//input[@name="signupstockpid"]/@value').extract()
        if identifier:
            yield Request(response.url, dont_filter=True, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        product_options = hxs.select('//div[@id="Product" and (div/text()="Product Options")]/table[@class="productOptions"][1]/tr/td[@class="name"]/a/@href').extract()
        for product_option in product_options:
            url = urljoin_rfc(get_base_url(response), product_option)
            yield Request(url, callback=self.parse_product)


        if not product_options:
            sku = hxs.select('//span[@itemprop="mpn"]/text()').extract()
            identifier = hxs.select('//div[@id="Product"]/div/form/table/tr/td/input[@name="PID"]/@value').extract()
            if not identifier:
                identifier = hxs.select('//input[@name="signupstockpid"]/@value').extract()
            if identifier:
                identifier = identifier[0]
            else:
                return

            option_ids = hxs.select('//select[@name="NewProductID"]/option/@value').extract()
            for option_id in option_ids:
                url = response.url.replace(identifier, option_id)
                yield Request(url, callback=self.parse_product, meta={'option': True})

            category = hxs.select('//div[@id="Breadcrumb"]/div/a/text()').extract()[-1]
            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('image_url', '//img[@id="productImg"]/@src')
            loader.add_value('category', category)
            loader.add_xpath('brand', '//div[p/text()="Manufacturer"]/a/img/@alt')
            loader.add_value('url', response.url)
            loader.add_xpath('name', '//div[@class="productTitle"]/h1/text()')

            loader.add_value('identifier', identifier)
            if sku:
                loader.add_value('sku', sku[0].replace(' ', ''))
            price = hxs.select('//td[@itemprop="price"]/text()').extract()
            if not price:
                price = hxs.select('//td[@itemprop="price"]/span[@class="pricemain"]/text()').extract()
                if not price:
                    price = hxs.select('//div[@id="Product"]//td[@class="price"]/span[@class="pricemain"]/text()').extract()

            if price:
                price = self.calculate_price(price[0])
            else:
                price = '0.0'
            loader.add_value('price', price)

            out_stock = 'CURRENTLY UNAVAILABLE' in ''.join(hxs.select('//div[@class="offerStock"]/p/text()').extract()).upper()
            if out_stock:
                loader.add_value('stock', 0)
            yield loader.load_item()

    def calculate_price(self, value):
        res = re.search(r'[.0-9]+', value)
        if res:
            price = Decimal(res.group(0))
            self.log("Price: %s" % price)
            return round((price) / Decimal('1.2'), 2)  # 20% EXC VAT
        else:
            return None
