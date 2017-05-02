import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip\
                             as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class SimplySupplementsSpider(BaseSpider):
    name = 'simplysupplements.net-merckgroup'
    allowed_domains = ['simplysupplements.net']
    start_urls = ('http://www.simplysupplements.net',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@class="sidebox"]//ul[@id="ailments"]/li//a')
        for category in categories:
            category_name = category.select('text()').extract()
            if category_name:
                url = urljoin_rfc(get_base_url(response), category.select('@href').extract()[0])
                yield Request(url, meta={'category':category_name[0]})

        products = hxs.select('//ul[@id="products"]/li/h2/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product, meta=response.meta)


    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//div[@class="innercol"]//h1/text()').extract()
        if name:
            main_id = hxs.select('//input[@name="product"]/@value').extract()[0]
            url = response.url
            url = urljoin_rfc(get_base_url(response), url)
            # skus = hxs.select('//td[@class="size"]/strong/text()').extract()
            # prices = hxs.select('//td[@class="price"]/text()').extract()
            # skus_prices = zip(skus, prices)
            items = hxs.select('//form[contains(@id, "add")]/table/tr')
            for item in items:
                sku = item.select('td[@class="size"]/strong/text()').extract()[0].strip(':')
                price = item.select('td[@class="price"]/text()').extract()[0]
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('url', url)
                loader.add_value('name', name[0].strip() + ' ' + sku)
                loader.add_value('price', price)
                loader.add_value('sku', sku)
                loader.add_value('category', response.meta.get('category'))
                loader.add_value('identifier', main_id + '-' + sku)
                image_url = hxs.select('//div[@id="sizes"]/div/center/img/@src').extract()
                if image_url:
                    image_url = urljoin_rfc(get_base_url(response), image_url[0])
                    loader.add_value('image_url', image_url)
                stock = 'IN STOCK' in ''.join(hxs.select('//div[@class="innercol"]/div/strong/text()').extract()).upper()
                if not stock:
                    loader.add_value('stock', 0)
                yield loader.load_item()
