# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.url import url_query_parameter


class OnestopDigitalSpider(BaseSpider):
    name = u'onestop-digital.com'
    allowed_domains = ['onestop-digital.com']
    start_urls = [
        'http://www.onestop-digital.com'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="vmenu_118"]/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//div[contains(@class,"product-container")]//a[@class="product-title"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # pagination
        for url in hxs.select('//div[@class="pagination"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)
        # subcategories
        for url in hxs.select('//table[@class="table-width subcategories"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories)

    @staticmethod
    def parse_product(response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//div[@class="border-image-wrap cm-preview-wrapper"]//img/@src').extract()
        product_identifier = url_query_parameter(response.url, 'product_id')
        product_name = hxs.select('//h1[@class="mainbox-title title-woutp"]/span/text()').extract()[0].strip()
        price = hxs.select('//span[@class="price-num"]/text()').extract()[1]
        price = extract_price(price)
        breadcrumbs = hxs.select('//div[@class="breadcrumbs clearfix"]//a/text()').extract()
        category = breadcrumbs[1]
        brand = breadcrumbs[2]
        in_stock = hxs.select('//span[@class="qty-in-stock"]/text()').extract()
        stock = True
        if not in_stock:
            stock = False
        elif in_stock[0] != 'In Stock':
            stock = False

        # options = hxs.select('//div[@class="cm-picker-product-options"]/div')

        # if not options:
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('sku', product_identifier)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        if not stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        yield product