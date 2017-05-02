# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price


class SoundsliveshopSpider(BaseSpider):
    name = u'soundsliveshop.com'
    allowed_domains = ['www.soundsliveshop.com']
    start_urls = ('http://www.soundsliveshop.com/', )

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//ul[@class="navLeft"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="listItems listItemsWhite"]//div[@class="listProductInfo"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        for url in hxs.select('//div[@class="pagingNew"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    @staticmethod
    def parse_product(response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = ''.join(hxs.select('//h1[@itemprop="name"]/text()').extract())
        if not name or 'B-STOCK' in name.upper():
            return
        loader.add_value('name', name)
        #identifier = hxs.select('//div[@class="detailsBoxDet"]//li[@class="textDBlue bold" and contains(text(), "Soundslive ID:")]/text()').re(r"(\d+)")
        #loader.add_value('identifier', identifier[0].strip())
        sku = hxs.select('//div[@class="detailsBoxDet"]//span[@itemprop="sku"]/text()').extract()
        loader.add_value('sku', sku[0].strip())
        loader.add_value('identifier', sku[0].strip())
        loader.add_value('url', response.url)
        image_url = hxs.select('//*[@id="ctl00_MainContentPlaceHolder_MainImage"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//span[@itemprop="price"]/@content').extract()
        if not price:
            return
        price = extract_price(price[0])
        loader.add_value('price', price)
        brand = hxs.select('//div[@class="ManInfoBox"]//strong[@itemprop="name"]/text()').extract()
        if brand:
            loader.add_value('brand', brand[0].strip())
        category = hxs.select('//*[@id="breadcrumb"]/li[3]/a/text()').extract()
        if category:
            loader.add_value('category', category[0])
        if price == 0:
            loader.add_value('stock', 0)
        stock = hxs.select('//span[@class="textOutOfStock"]/text()').extract()
        if stock:
            if stock[0] == 'preorder':
                loader.add_value('stock', 0)
        yield loader.load_item()
