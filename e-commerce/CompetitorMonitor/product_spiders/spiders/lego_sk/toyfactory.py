# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
from urlparse import urljoin as urljoin_rfc
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class ToyfactorySkSpider(LegoMetadataBaseSpider):
    name = u'toyfactory.sk'
    allowed_domains = ['www.toyfactory.sk']
    start_urls = [
        u'http://www.toyfactory.sk/hracky/lego/',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #categories
        urls = hxs.select('//div[@class="kategoriaNahlady"]//span[@class="nadpis"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        #categories
        urls = hxs.select('//div[@class="kategoriaNahlady"]//span[@class="nadpis"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)
        #pagination
        urls = hxs.select('//div[@class="strankovanie-inner"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)
        #products
        category = hxs.select('//*[@id="main"]/h1/text()').extract()
        products = hxs.select('//div[@class="produkty"][1]/div[@class="produkt"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//div[@class="nazov"]/a/text()').extract()[0].strip()
            url = product.select('.//div[@class="nazov"]/a/@href').extract()[0]
            loader.add_value('url', urljoin_rfc(base_url, url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', './/a[@class="obrazok"]/img/@src',
                             Compose(lambda v: urljoin(base_url, v[0])))
            price = product.select('.//div[@class="cena"]/text()').extract()
            price = extract_price_eu(price[0].strip())
            loader.add_value('price', price)
            results = re.search(r"\b([\d]+)\b", name)
            if results:
                sku = results.group(1)
                loader.add_value('sku', sku)
            loader.add_value('brand', 'LEGO')
            availability = product.select('.//a[@class="kosik vypredane"]').extract()
            if availability:
                loader.add_value('stock', 0)
            if category:
                category = category[0].partition(' - strana ')[0]
                loader.add_value('category', category)
            identifier = product.select('.//a[@class="kosik"]/@href').extract()
            if identifier:
                identifier = identifier[0].partition('=')[2]
                loader.add_value('identifier', identifier)
                yield self.load_item_with_metadata(loader.load_item())
            else:
                #as we have no identifier for out of stock products we need to visit product page to extract it
                product = loader.load_item()
                yield Request(product['url'], callback=self.parse_identifier, meta={'product': product})

    def parse_identifier(self, response):
        hxs = HtmlXPathSelector(response)
        product = response.meta.get('product')
        identifier = hxs.select('//input[@id="pes_tovar_id"]/@value').extract()[0]
        product['identifier'] = identifier
        yield self.load_item_with_metadata(product)
