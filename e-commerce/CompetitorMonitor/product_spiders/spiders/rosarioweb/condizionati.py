# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price_eu as extract_price
import re
import json


def get_links(item):
    if len(item) > 5:
        for i in xrange(5, len(item)):
            for link in get_links(item[i]):
                yield link
    else:
        yield item[2]


class CondizionatiSpider(BaseSpider):
    name = u'condizionati.com'
    allowed_domains = ['www.condizionati.com']
    start_urls = ('http://www.condizionati.com/condizionatori/', )

    def parse(self, response):
        base_url = get_base_url(response)
        match = re.search(r"var catTree =(.*?)\];", response.body_as_unicode(), re.DOTALL | re.IGNORECASE)
        data = match.group(1).strip().replace("\\'", "").replace("'", '"').replace('\n', '') + ']'
        data = json.loads(data, encoding='utf8')
        for item in data:
            for url in get_links(item):
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    def parse_product_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        category = hxs.select('//a[@class="breadcrumb"][2]/@title').extract()[0]
        for url in hxs.select('//td[@class="productListingBlock-data"]//a[@class="productListBlockCell_plink"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})
        for url in hxs.select('//a[@class="pageResults" and @title=" Pagina successiva "]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product_list)

    @staticmethod
    def parse_product(response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//b[@class="prod-title-caption"]/text()').extract()[0]
        loader.add_value('name', name)
        identifier = hxs.select('//input[@name="products_id"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        sku = hxs.select('//span[@class="smallTextProdInfo"]/text()').extract()
        if sku:
            loader.add_value('sku', sku[0].strip()[1:-1])
        loader.add_value('url', response.url)
        image_url = hxs.select('//*[@id="prodImageCell"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//span[@class="listprice_nospecial"]/text()').extract()
        price = extract_price(price[0].replace(' ', ''))
        loader.add_value('price', price)
        brand = hxs.select('//*[@id="manufacturer_info"]//td[@class="main"]/b/text()').extract()
        if brand:
            loader.add_value('brand', brand[0])
        loader.add_value('category', response.meta['category'])
        yield loader.load_item()