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


class BabalooSkSpider(LegoMetadataBaseSpider):
    name = u'babaloo.sk'
    allowed_domains = ['www.babaloo.sk']
    start_urls = [
        'http://www.babaloo.sk/babaloo/eshop/13-1-LEGO',
        'http://www.babaloo.sk/babaloo/eshop/1-1-LEGO-duplo'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #categories
        urls = hxs.select('//*[@id="incenterpage2"]//p[@style="text-align: center;"]//a/@href').extract()
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
        category = hxs.select('//*[@id="wherei"]/p//a/text()').extract()
        products = hxs.select('//div[@class="productBody"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//div[@class="productTitleContent"]/a/text()').extract()[0].strip()
            url = product.select('.//div[@class="productTitleContent"]/a/@href').extract()[0]
            loader.add_value('url', urljoin_rfc(base_url, url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', './/div[@class="img_box"]/a/img[1]/@src',
                             Compose(lambda v: urljoin(base_url, v[0])))
            price = product.select('.//div[@class="productPrice"]/span[contains(@itemprop, "price")]/text()').extract()[0]
            price = price.split(u'\xa0')[0]
            price = extract_price_eu(price)
            loader.add_value('price', price)
            results = re.search(r"\b([\d]+)\b", name)
            if results:
                loader.add_value('sku', results.group(1))
            identifier = product.select('.//div[@class="img_box"]/a/img[1]/@rel').extract()[0]
            loader.add_value('identifier', identifier)
            loader.add_value('brand', 'LEGO')
            stock = product.select('.//div[@class="stock_no"]').extract()
            if stock:
                loader.add_value('stock', 0)
            if category:
                loader.add_value('category', category[-1])
            if price < 15:
                loader.add_value('shipping_cost', 2.69)
            yield self.load_item_with_metadata(loader.load_item())
