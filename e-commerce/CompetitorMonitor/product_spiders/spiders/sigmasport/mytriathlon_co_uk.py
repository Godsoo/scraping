# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import itertools

from product_spiders.base_spiders.primary_spider import PrimarySpider

from sigmasportitems import SigmaSportMeta, extract_exc_vat_price

class MytriathlonSpider(PrimarySpider):
    name = u'sigmasport-mytriathlon.co.uk'
    allowed_domains = ['mytriathlon.co.uk']
    start_urls = [
        'http://mytriathlon.co.uk/?setCurrencyId=1'
    ]

    csv_file = 'mytriathlon.co.uk_crawl.csv'

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@class="category-list"]/li[position() >= 1 and not(position() > 5)]//li//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # products
        for url in hxs.select('//ul[@class="ProductList"]//div[@class="ProductDetails"]/span[@class="ProductName"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # pagination
        for url in hxs.select('//ul[@class="pagination"]/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        image_url = hxs.select('//a[@itemprop="image"]/@href').extract()
        try:
            product_identifier = hxs.select('//*[@id="productDetailsAddToCartForm"]/input[@name="product_id"]/@value').extract()[0].strip()
        except:
            return
        product_name = hxs.select('//*[@id="ProductDetails"]/h1/text()').extract()[0].strip()
        category = hxs.select('//ul[@class="breadcrumbs"]//a/text()').extract()[1:]
        brand = hxs.select('//*[@id="ProductDetails"]/div[@itemprop="brand"]//span/text()').extract()
        brand = brand[0].strip() if brand else ''
        product_price = hxs.select('//span[@class="ProductPrice VariationProductPrice"]/text()').extract()[0]
        product_price = extract_price(product_price)
        options = []
        product_options = hxs.select('//div[@class="productOptionViewRadio"]')
        if product_options:
            for select in product_options:
                values = select.select('.//li/label/input/@value').extract()
                titles = select.select('.//li/label/span/text()').extract()
                opts = []
                for value, title in zip(values, titles):
                    opts.append({'identifier': value, 'name': title})
                if opts:
                    options.append(opts)
        product_options = hxs.select('//div[@class="productOptionViewSelect"]')

        if product_options:
            for select in product_options:
                values = select.select('./select/option/@value').extract()
                titles = select.select('./select/option/text()').extract()
                opts = []
                for value, title in zip(values, titles):
                    if value:
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
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                product_loader.add_value('price', product_price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                product = product_loader.load_item()
                metadata = SigmaSportMeta()
                metadata['price_exc_vat'] = extract_exc_vat_price(product)
                product['metadata'] = metadata
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('price', product_price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            product = product_loader.load_item()
            metadata = SigmaSportMeta()
            metadata['price_exc_vat'] = extract_exc_vat_price(product)
            product['metadata'] = metadata
            yield product
