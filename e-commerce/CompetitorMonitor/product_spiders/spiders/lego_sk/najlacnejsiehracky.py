# -*- coding: utf-8 -*-
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class NajlacnejsiehrackySkSpider(LegoMetadataBaseSpider):
    name = u'najlacnejsiehracky.sk'
    allowed_domains = ['www.najlacnejsiehracky.sk']
    start_urls = [
        u'http://www.najlacnejsiehracky.sk/index.php?route=product/search&search=Lego',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #pagination
        urls = hxs.select('//div[@class="pagination"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)
        #products
        products = hxs.select('//div[@class="product-grid"]/div')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//div[@class="image"]/a/img/@alt').extract()[0].strip()
            url = product.select('.//div[@class="image"]/a/@href').extract()[0]
            loader.add_value('url', urljoin_rfc(base_url, url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', './/div[@class="image"]/a/img/@src',
                             Compose(lambda v: urljoin(base_url, v[0])))
            price = product.select('.//div[@class="price"]/span[@class="price-tax"]/text()').extract()
            price = extract_price(price[0].strip())
            loader.add_value('price', price)
            results = re.search(r"\b([\d]+)\b", name)
            if results:
                loader.add_value('sku', results.group(1))
            identifier = product.select('.//div[@class="cart"]/input/@onclick').re(r"([\d]+)")[0]
            loader.add_value('identifier', identifier)
            loader.add_value('brand', 'LEGO')
            loader.add_value('shipping_cost', 4.89)
            yield self.load_item_with_metadata(loader.load_item())
