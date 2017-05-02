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

class HealthSpanSpider(BaseSpider):
    name = 'healthspan.co.uk-merckgroup'
    allowed_domains = ['www.healthspan.co.uk', 'healthspan.co.uk']
    start_urls = ('http://www.healthspan.co.uk/products/',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        hxs = HtmlXPathSelector(response)
        links = hxs.select(u'//div[@id="listtable"]//tr/td/span/a/@href').extract()
        for prod_url in links:
            url = urljoin_rfc(get_base_url(response), prod_url)
            yield Request(url, callback=self.parse_product)


        categories = hxs.select('//div[@class="category-nav"]/ul/li/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        products = hxs.select('//div[@id="products_list"]/div[contains(@class, "item")]/div/h2/a/@href').extract()
        products += hxs.select('//div[@class="hero_second"]/div/h2/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        next = hxs.select('//a[contains(@id, "NextPage")]/@href').extract()
        if next:
            next_url = urljoin_rfc(get_base_url(response), next[0])
            yield Request(next_url)


    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//h1[@itemprop="name"]/span/text()').extract()
        if name:
            url = response.url
            url = urljoin_rfc(get_base_url(response), url)
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', url)
            loader.add_value('name', name[0])

            items = hxs.select('//div[@class="sku-details"]')
            for item in items:
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('url', url)

                n = name[0].strip()
                desc = ''.join(item.select('.//span[@class="sku-description"]//text()').extract())
                if desc:
                    n += ' ' + desc.strip()
                sku = item.select('span/input[@class="addToBasketDetails"]/@value').extract()
                sku = sku[0] if sku else ''

                loader.add_value('identifier', sku)
                loader.add_value('sku', sku)

                loader.add_value('name', n)
                price = item.select('./span[@class="price"]/text()').extract()
                if price:
                    loader.add_value('price', price[0])
                else:
                    price = item.select('./span[@class="special-price"]/text()').extract()
                    loader.add_value('price', price[0])
                category = hxs.select('//div[@id="breadcrumb"]//a/text()').extract()
                category = category[-2] if category else ''
                loader.add_value('category', category)

                image_url = hxs.select('//div[@id="main-img"]//img/@src').extract()
                if image_url:
                    image_url = urljoin_rfc(get_base_url(response), image_url[0])
                    loader.add_value('image_url', image_url)

                yield loader.load_item()
