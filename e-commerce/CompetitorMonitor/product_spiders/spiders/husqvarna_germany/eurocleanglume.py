import re
import os
import hashlib
import csv
from decimal import Decimal
from urllib import urlencode

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from product_spiders.utils import extract_price

import itertools
import json
import copy

HERE = os.path.abspath(os.path.dirname(__file__))

class EurocleanglumeSpider(BaseSpider):
    name = 'husqvarna_germany-eurocleanglume.de'
    allowed_domains = ['eurocleanglume.de']
    start_urls = ('http://www.eurocleanglume.de',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="HorizontalDisplay  NavBarElement0 DropDownList"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        next_page = hxs.select('//ul[@class="PagerSizeContainer"]/li/a[text()=">"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//a[@title="Zum Produkt"]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), selector=hxs)

        identifier = hxs.select('//span[@class="ProductNo DisplayBlock SmallTopMargin"]/text()').re('Artikel-Nr\.: (.*)')
        loader.add_value('identifier', identifier)

        loader.add_value('sku', identifier)

        name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        loader.add_value('name', name[0])

        loader.add_value('url', response.url)
        
        price = response.xpath('//span[@itemprop="price"]/text()').extract()
        price = price[0] if price else '0.00'
        loader.add_value('price', price)

        price = loader.get_output_value('price')
        if price and Decimal(price) <= 49.99:
            loader.add_value('shipping_cost', '4.99')

        category = hxs.select('//a[@class="BreadcrumbItem"]/span/text()').extract()
        category = ' > '.join(category[1:-1] if len(category) > 2 else '')
        loader.add_value('category', category)

        image_url = hxs.select('//div[@class="ProductImage"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        yield loader.load_item()

        if response.meta.get('options_crawled', False):
            log.msg('Option found: ' + response.url)
            return

        primary_options = hxs.select('//select[@id="SelectedVariation0"]/option/@value').extract()
        for primary_option in primary_options:
            secondary_options = hxs.select('//select[@id="SelectedVariation1"]/option/@value').extract()
            if not secondary_options:
                formdata = {'ChangeAction': 'SelectSubProduct',
                            'SelectedVariation': primary_option}
                yield FormRequest(response.url, dont_filter=True, formdata=formdata, meta={'options_crawled': True}, callback=self.parse_product)
            else:
                for secondary_option in secondary_options:
                    formdata = {'ChangeAction': 'SelectSubProduct',
                                'SelectedVariation': [primary_option, secondary_option]}
                    yield FormRequest(response.url, dont_filter=True, formdata=formdata, meta={'options_crawled': True}, callback=self.parse_product)
