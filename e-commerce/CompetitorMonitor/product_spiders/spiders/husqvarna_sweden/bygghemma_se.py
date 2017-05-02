# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc


class BygghemmaSeSpider(BaseSpider):
    name = u'husqvarna_sweden-bygghemma.se'
    allowed_domains = ['bygghemma.se']
    start_urls = [
        'http://www.bygghemma.se/tradgard-och-utemiljo/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="categoryPanel"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?showall=true'), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # pages
        for url in hxs.select('//div[@class="pager"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)
        # products
        for url in hxs.select('//div[@class="product_container"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        # subcategories
        for url in hxs.select('//div[@class="categoryPanel"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url + '?showall=true'), callback=self.parse_products_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)

        image_url = hxs.select('//img[@property="image"]/@src').extract()
        product_identifier = hxs.select('//script/text()').re("'productId': *(.+),")
        product_name = hxs.select('//script/text()').re("'name': *\"(.+)\"")
        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//script/text()').re("'price': *\"(.+)\"")
        sku = hxs.select('//script/text()').re('"ArtNbr":"(.+?)"')
        product_loader.add_value('sku', sku[-1])
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        category = hxs.select('//div[@class="breadcrumb gridle_container"]/a/text()').extract()[1:-1]
        category = category[-3:]
        product_loader.add_value('category', category)
        brand = hxs.select('//script/text()').re("'brand': *\"(.+)\"")
        product_loader.add_value('brand', brand)
        product = product_loader.load_item()
        yield product