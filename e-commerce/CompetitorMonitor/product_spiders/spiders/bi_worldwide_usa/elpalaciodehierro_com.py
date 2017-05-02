# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price


class ElpalaciodehierroSpider(BaseSpider):
    name = u'bi_worldwide_usa-elpalaciodehierro.com'
    allowed_domains = ['www.elpalaciodehierro.com']
    start_urls = ('http://www.elpalaciodehierro.com/', )

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="nav"]//dt[@class="level1"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@class="image-banner type-image"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

        for url in hxs.select('//ul[@class="products-grid"]/li//h3/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    @staticmethod
    def parse_product(response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        brand = hxs.select('//h2[@itemprop="brand"]/text()').extract()
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        loader.add_value('name', name)
        price = hxs.select('//*[@id="product_addtocart_form"]//span[@class="price"]/text()').extract()
        price = extract_price(price[0])
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        identifier = hxs.select('//p[@class="product-ids"]/text()').extract()[0]
        identifier = identifier.replace('SKU# ', '')
        loader.add_value('identifier', identifier)
        sku = hxs.select('//td[@class="colleft" and text()="modelo"]/following-sibling::td/text()').extract()
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text()').extract()
        category = category[-1].strip() if category else ''
        loader.add_value('category', category)
        image_url = hxs.select('//*[@id="main-image"]/@href').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        yield loader.load_item()