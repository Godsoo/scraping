# -*- coding: utf-8 -*-
"""
Customer: Specsavers IE
Website: https://www.feelgoodcontacts.ie
Extract all product information

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4560-specsavers-ie---new-site---feel-good-contact-lenses/details#

"""

import urlparse
import os

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


class FeelgoodContactsSpider(BaseSpider):
    name = 'specsavers_ie-feelgoodcontacts.ie'
    allowed_domains = ['feelgoodcontacts.ie']
    start_urls = ['https://www.feelgoodcontacts.ie/catalogue/all-contact-lenses']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        # categories and subcategories
        categories = response.xpath('//div[contains(@class, "categories")]//a/@href').extract()
        categories += response.xpath('//a[contains(@class, "btn") and contains(text(), "range")]/@href').extract()
        for cat_href in categories:
            yield Request(urlparse.urljoin(get_base_url(response), cat_href))

        # products
        products = response.xpath('//a[div[@class="product-box-div-all"]]/@href').extract()
        products += response.xpath('//a[@class="prodname"]/@href').extract()
        for url in products:
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        url = response.url

        l = ProductLoader(item=Product(), response=response)

        name = response.xpath('//h1/text()').extract()[0].strip()
        l.add_value('name', name)


        price = response.xpath('//div[@class="prod-qty priceperbox"]/span/text()').extract()
        if not price:
            price = response.xpath('//span[contains(@id, "litPricePerBoxSupplySolution")]/text()').extract()

        try:
            price = extract_price(price[0])
        except IndexError:
            return
        l.add_value('price', price)

        identifier = response.xpath('//input[@id="hdnProductId"]/@value').extract()[0]
        l.add_value('identifier', identifier)
        l.add_value('sku', identifier)
        brand = response.xpath('//a[@title="Brand"]/span/text()').extract()
        if not brand:
            brand = response.xpath('//a[@id="MainContent_cntMain_aManufactureSolution"]/@title').extract()

        brand = brand[0].strip() if brand else ''
        l.add_value('brand', brand)
        categories = map(lambda x: x.strip(), response.xpath('//div[@class="breadcrumbs"]//a/span/text()').extract())[1:]
        l.add_value('category', categories)
        image_url = response.xpath('//li[@class="image1"]//img/@src').extract()
        if image_url:
            l.add_value('image_url', urlparse.urljoin(get_base_url(response), image_url[0]))
        l.add_value('url', url)
        l.add_value('shipping_cost', 0)


        product = l.load_item()


        yield product
