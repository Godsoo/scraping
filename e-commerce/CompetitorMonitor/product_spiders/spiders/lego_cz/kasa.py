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


class KasaCzSpider(LegoMetadataBaseSpider):
    name = u'kasa.cz'
    allowed_domains = ['www.kasa.cz']
    start_urls = [
        u'http://www.kasa.cz/hracky/lego/?limit=96',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # pagination
        urls = hxs.select('//ul[@class="paging_paging"]//a[@class="pg_button"]/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)
        #products
        urls = hxs.select('//div[@class="list_products clearfix"]/div[contains(@class, "product")]//h2/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@id="detail_product"]//h1/text()').extract()[0].strip()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//*[@id="image_content"]/a/img/@src',
                         Compose(lambda v: urljoin(base_url, v[0])))
        price = hxs.select('//*[@id="real_price"]/text()').extract()
        price = extract_price(price[0].strip().replace(u' K\u010d', '').replace(',', '.').replace(' ', ''))
        loader.add_value('price', price)
        category = hxs.select('//*[@id="breadcrumbs"]/a[@class="item"]/text()').extract()
        if category:
            loader.add_value('category', category[-1])
        results = re.search(r"([\d]+)", name)
        if results:
            loader.add_value('sku', results.group(1))
        identifier = hxs.select('//p[@class="warehouse"]/a/@onclick').re(r"([\d]+)")[0]
        loader.add_value('identifier', identifier)
        availability = hxs.select('//p[@class="warehouse"]/a/span/text()').extract()[0].strip()
        if availability == u'Nen\xed skladem' or availability == u'U dodavatele':
            loader.add_value('stock', 0)
        else:
            results = re.search(r"([\d]+)", availability)
            if results:
                loader.add_value('stock', results.group(1))
        loader.add_value('brand', 'LEGO')
        yield self.load_item_with_metadata(loader.load_item())
