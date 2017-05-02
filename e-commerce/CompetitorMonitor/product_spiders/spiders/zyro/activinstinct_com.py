# -*- coding: utf-8 -*-
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import itertools


class ActivinstInctSpider(BaseSpider):
    name = u'zyro-activinstinct.com'
    allowed_domains = ['activinstinct.com']
    start_urls = [
        'http://www.activinstinct.com/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@id="navigation"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        # products
        products = hxs.select('//div[@class="product_item"]//a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        # pagination
        next_page = hxs.select('//a[@class="next"]/@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(urljoin_rfc(base_url, url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//span[@class="mainimage"]//img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        product_identifier = hxs.select('//script/text()').re('var product_id *= *(.+);')
        if not product_identifier:
            yield Request(response.url, dont_filter=True)
            return
        product_identifier = product_identifier[0]
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        category = hxs.select('//div[@id="breadcrumbs"]//a/text()').extract()[1:]
        brand = re.findall("'brand': '(.*)',", response.body)
        brand = brand[0].strip() if brand else ''
        product_price = hxs.select('//script/text()').re("'price' *: *'(.+?)'")[0]
        product_price = extract_price(product_price)
        sku = hxs.select('//span[@class="mpn"]//text()').re('Product code: *(.+)')

        options = []
        product_options = hxs.select('//div[@class="ctaselector"]')
        if product_options:
            for select in product_options:
                values = select.select('.//li/a/@id').extract()
                titles = select.select('.//li/a/span/text()').extract()
                opts = []
                for value, title in zip(values, titles):
                    opts.append({'identifier': value, 'name': title})
                if opts:
                    options.append(opts)

        if options:
            for opts in itertools.product(*options):
                name = product_name
                identifier = product_identifier
                for option in opts:
                    name += ' ' + option['name']
                    identifier += '_' + option['identifier']
                product_loader = ProductLoader(item=Product(), selector=hxs)
                product_loader.add_value('identifier', identifier)
                product_loader.add_value('name', name)
                if image_url:
                    product_loader.add_value('image_url', image_url)
                product_loader.add_value('price', product_price)
                if product_loader.get_output_value('price')<50:
                    product_loader.add_value('shipping_cost', 3.95)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('sku', sku)
                product_loader.add_value('category', category)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', image_url)
            product_loader.add_value('price', product_price)
            if product_loader.get_output_value('price')<50:
                product_loader.add_value('shipping_cost', 3.95)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('sku', sku)
            product_loader.add_value('category', category)
            product = product_loader.load_item()
            yield product
