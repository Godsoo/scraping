# -*- coding: utf-8 -*-
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import extract_price, fix_spaces

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class WalmartSpider(BaseSpider):
    name = "legocanada-walmart.ca"
    allowed_domains = ["walmart.ca"]
    start_urls = ["http://www.walmart.ca/en/toys/lego/N-110+1019588"]

    rotate_agent = True

    _re_sku = re.compile('(\d\d\d\d\d?)')

    def parse(self, response):
        categories = response.xpath('//div[contains(@class, "md_5box_box")]/a/@href').extract()
        if not categories:
            yield response.request
            return
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_category)

    def parse_category(self, response):
        next_url = response.xpath('//a[@id="loadmore"]/@href').extract()
        if next_url:
            yield Request(response.urljoin(next_url[0]), callback=self.parse_category)

        product_urls = response.xpath('//div[@class="details"]/div/h1/a/@href').extract()
        for url in product_urls:
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())

        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        name = fix_spaces(name)
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        price = hxs.select('//div[@class="pricing-shipping"]/div/span[@itemprop="price"]//text()').extract()
        price = extract_price(price[0]) if price else '0'
        loader.add_value('price', price)

        img_url = hxs.select('//img[@class="image"]/@src').extract()
        if img_url:
            loader.add_value('image_url', urljoin(base_url, img_url[0]))

        loader.add_value('category', 'Lego')
        loader.add_value('brand', 'Lego')

        identifier = response.xpath('//form[contains(@class, "product-purchase")]/@data-rollup-id').extract()

        if not identifier:
            log.msg('ERROR >>> Product without identifier: ' + response.url)
            return

        loader.add_value('identifier', identifier[0])

        sku = self._re_sku.findall(name)
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)

        out_of_stock = 'OUT OF STOCK' in ''.join(hxs.select('//div[@class="shipping status"]/span/text()').extract()).upper()
        if out_of_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
