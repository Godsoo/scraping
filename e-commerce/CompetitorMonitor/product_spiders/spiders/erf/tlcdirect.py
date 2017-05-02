# -*- coding: utf-8 -*-

"""
ERF account
TLC Direct spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5489
"""
import re

from scrapy import Spider
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.items import Product, \
    ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import extract_price


class TlcDirectSpider(Spider):
    name = 'erf-tlc-direct.co.uk'
    allowed_domains = ['tlc-direct.co.uk']

    start_urls = ('https://www.tlc-direct.co.uk/',)

    def parse(self, response):
        cats = response.xpath('//nav[@class="main-index"]//a/@href').extract()
        for cat in cats:
            yield Request(response.urljoin(cat), callback=self.parse_subcats)

    def parse_subcats(self, response):
        subcats = response.xpath('//ul[@class="category-panel__menu"]//a[@class="menu-item__link"]/@href').extract()
        for cat in subcats:
            yield Request(urljoin_rfc(get_base_url(response), cat),
                          callback=self.parse_subcats)

        products = response.xpath('//section[contains(@class, "product-table__tr")]')
        for product in products:
            product_url = product.xpath('.//h3/a/@href').extract()[0]
            yield Request(response.urljoin(product_url), callback=self.parse_product)

    def parse_product(self, response):
        categories = response.xpath('//nav[@class="breadcrumbs"]//a/text()').extract()

        price = response.xpath('//div[@id="order"]//div[contains(@class, "product__price--ex-vat")]'
                               '//td[@class="price-breaks__price"]/p/text()').extract()
        price = extract_price(price[0]) if price else 0

        sku = response.xpath('//div[@id="order"]//h2[contains(@class, "product__order-code")]/text()').extract()
        sku = sku[0].strip().split()[-1] if sku else ''
        image_url = response.xpath('//div[@id="order"]//a[@class="group__image"]/img/@src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''

        identifier = response.xpath('//div[@id="order"]//input[@class="update-cart__quantity"]/@id').re('product-(.*)')
        if not identifier:
            identifier = re.findall("'ecomm_prodid': \[\'(.*)\'", response.body)[0]

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//div[@id="order"]/h1/span[@class="heading__title"]/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('image_url', image_url)
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        loader.add_value('category', categories)
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', 3.60)
        out_of_stock = response.xpath('//div[@id="order"]//div[contains(@class, "product__quantity")]'
                                      '/div/p[contains(text(), "All Sold")]')
        if out_of_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
