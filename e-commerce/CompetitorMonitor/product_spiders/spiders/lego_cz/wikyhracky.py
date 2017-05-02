# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class WikyhrackyCzSpider(LegoMetadataBaseSpider):
    name = u'wikyhracky.cz'
    allowed_domains = ['www.wikyhracky.cz']
    start_urls = [
        u'http://www.wikyhracky.cz/lego-1/?onpage=10000',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcategories
        urls = hxs.select('//*[@id="content_in"]//h2/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@id="detail"]/h1/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//*[@id="preview_image"]/@src',
                         Compose(lambda v: urljoin(base_url, v[0])))
        price = hxs.select('//div[@class="rLine prices mainPrice"]/div[@class="value"]/text()').extract()
        price = extract_price(price[0].strip().replace(u' K\u010d', '').replace(',', '.').replace(' ', ''))
        loader.add_value('price', price)
        category = hxs.select('//span[@class="znacka"]/a/text()').extract()
        if category:
            loader.add_value('category', category[0])
        sku = ''
        for match in re.finditer(r"([\d]+)", name):
            if len(match.group()) > len(sku):
                sku = match.group()
        loader.add_value('sku', sku)
        identifier = hxs.select('//*[@id="detail_price"]//input[@name="id_product"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        availability = hxs.select('//div[@class="rLine dostupnost"]/div[@class="value"]/text()').extract()[0].strip()
        if availability == u'Nen\xed skladem':
            loader.add_value('stock', 0)
        loader.add_value('brand', 'LEGO')
        if int(price) <= 1500:
            loader.add_value('shipping_cost', 69)
        yield self.load_item_with_metadata(loader.load_item())
