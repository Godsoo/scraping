# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
from urlparse import urljoin as urljoin_rfc
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class RajhraciekSkSpider(LegoMetadataBaseSpider):
    name = u'rajhraciek.sk'
    allowed_domains = ['www.rajhraciek.sk']
    start_urls = [
        u'http://www.rajhraciek.sk/lego-c1_1729',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #categories
        urls = hxs.select('//*[@id="navig-left"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        urls = hxs.select('//ul[@class="pager"]/li[@class!="selected"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)
        #products
        category = hxs.select('//*[@id="listing_h1"]/h1/text()').extract()
        products = hxs.select('//*[@id="listing_products2"]/div[@class="product"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//div[@class="product_title"]/h2/a/text()').extract()[0].strip()
            url = product.select('.//div[@class="product_title"]/h2/a/@href').extract()[0]
            loader.add_value('url', urljoin_rfc(base_url, url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', './/div[@class="product_image"]/a/img/@src',
                             Compose(lambda v: urljoin(base_url, v[0])))
            price = product.select('.//span[@class="price"]/text()').extract()[0]
            price = price.split(u'\xa0')[0]
            price = extract_price_eu(price)
            loader.add_value('price', price)
            sku = product.select('.//table/tr[1]/td[2]/strong/text()').extract()
            if sku:
                loader.add_value('sku', sku[0])
            identifier = product.select('.//div[@class="product_title"]/h2/a/@href').re(r"-p([\d]+)$")[0]
            loader.add_value('identifier', identifier)
            loader.add_value('brand', 'LEGO')
            stock = product.select('.//table//span[@class="skladom"]/text()').extract()
            if stock:
                results = re.search(r"\b([\d]+)\b", stock[0])
                if results:
                    loader.add_value('stock', results.group(1))
            if category:
                loader.add_value('category', category[0])
            yield self.load_item_with_metadata(loader.load_item())
