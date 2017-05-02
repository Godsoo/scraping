# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price_eu as extract_price


class ClimamarketItSpider(BaseSpider):

    name = u'climamarket.it'
    allowed_domains = ['www.climamarket.it']
    start_urls = ('http://www.climamarket.it/cerca?page=1&per_page=52&t=', )


    def parse(self, response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@id="mainmenu"]/ul/li/a/@href').extract()
        categories += hxs.select('//a[@class="catName"]/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse)

        products = hxs.select('//p[@class="descShort"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next = hxs.select('//li[@class="next"]/a/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse)


    @staticmethod
    def parse_product(response):

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select("//span[@itemprop='name']/text()").extract()[0]
        loader.add_value('name', name)
        identifier = hxs.select('//a[@class="addToFavorites"]/@data-product').extract()
        if not identifier:
            return
        loader.add_value('identifier', identifier[0])
        sku = hxs.select('//p[@class="code"]/span/text()').extract()
        if sku:
            loader.add_value('sku', sku[0].strip())
        loader.add_value('url', response.url)
        image_url = hxs.select('//img[@class="callToZoom"]/@src').extract()
        if image_url:
            image_url = image_url[0]
            if '?' in image_url:
                image_url = image_url.split('?')[0]
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        price = ''.join(hxs.select('//p[contains(@class, "priceBig")]//text()').extract()).strip()
        if not price:
            return
        price = extract_price(''.join(price))
        loader.add_value('price', price)
        brand = hxs.select('//div[contains(text(), "Marca")]/span/text()').extract()
        if brand:
            loader.add_value('brand', brand[0].strip())
        category = ''.join(hxs.select('//span[contains(text(), "Macro Tipologia")]/following::span[1]/text()').extract()).strip()
        loader.add_value('category', category)
        yield loader.load_item()
