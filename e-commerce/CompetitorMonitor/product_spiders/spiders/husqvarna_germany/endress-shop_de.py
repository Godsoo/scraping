# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc
import re

from copy import deepcopy


class EndressShopDeSpider(BaseSpider):
    name = u'husqvarna_germany-endress-shop.de'
    allowed_domains = ['endress-shop.de']
    start_urls = [
        'https://www.endress-shop.de/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//ul[@class="nav navbar-nav"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):

        # products
        for url in response.xpath('//div[@class="product-item-body"]//div[@class="text"]/a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_product)
        # subcategories
        for url in response.xpath('//div[@class="teaser-text"]/a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        image_url = response.xpath('//div[contains(@class, "productImage")]/img[@class="img-responsive"]/@src').extract()
        product_identifier = response.xpath('//input[@id="product_buy_id"]/@value').extract()[0]
        product_name = response.xpath('//div[contains(@class, "prod_description")]/h1/text()').extract()[0].strip()
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url[0].strip()))
        price = response.xpath('//div[@class="price-box"]/div[@class="price"]/text()').extract()
        price = extract_price(price[0])
        sku = ''.join(response.xpath('//tr[td[contains(text(), "Art")]]/td[@class="attributvalue"]/text()').extract()).strip()
        product_loader.add_value('sku', sku)
        brand = response.xpath('//tr[td[contains(text(), "Hersteller")]]/td[@class="attributvalue"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        product_loader.add_value('brand', brand)

        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        category = response.xpath('//div[@id="breadcrumb"]//a/text()').extract()[2:-1]
        product_loader.add_value('category', category)

        match = response.xpath('//tr[td[contains(text(), "Gewicht")]]/td[@class="attributvalue"]/text()').re('\d,\d+')
        if match:
            try:
                weight = float(match.replace(',', '.'))
                if weight <= 2:
                    product_loader.add_value('shipping_cost', 5)
                elif weight <= 40:
                    product_loader.add_value('shipping_cost', 8)
                elif weight <= 60:
                    product_loader.add_value('shipping_cost', 15)
                elif weight <= 100:
                    product_loader.add_value('shipping_cost', 80)
                elif weight > 100:
                    product_loader.add_value('shipping_cost', 150)
            except:
                pass
        out_of_stock = response.xpath(u'//div[@class="deliveryStatus"]/span[contains(text(), "Nicht Versandfähig")]')
        if out_of_stock:
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()

        options = response.xpath('//select[@id="option_Memory"]/option')
        if options:
            for option in options:
                product_option = deepcopy(product)
                product_option['identifier'] += '-' + option.select('@value').extract()[0]
                product_option['name'] += ' ' + ''.join(option.select('text()').extract())
                product_option['price'] = extract_price(option.select('@data-src').extract()[0])
                yield product_option
        else:
            yield product
