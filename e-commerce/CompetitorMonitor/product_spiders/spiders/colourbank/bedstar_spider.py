# -*- coding: utf-8 -*-

import os
import re
from decimal import Decimal
from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin as urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class ColourbankBedstarCoUkSpider(BaseSpider):
    name = "colourbank-bedstar.co.uk"
    start_urls = ['http://bedstardirect.co.uk/']
    allowed_domains = ['bedstardirect.co.uk', 'bedstar.co.uk']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for li in hxs.select(u'//ul[@class="main-ul"]/li'):
            for url in li.select(u'.//a/@href').extract():
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product_list,
                              meta={'category': li.select('./a/text()').extract()})

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="nav-pages"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url.split('?')[0], callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[@class="nav-pages"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

        for url in hxs.select(u'//div[@class="product_block"]/h2/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        for url in hxs.select('//div[@class="override-block"]/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        identifier = hxs.select(u'//form[@name="orderform"]/input[@name="productid"]/@value').extract()

        if identifier:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('url', response.url)
            product_loader.add_xpath('name', u'//h1[@class="dialog_title"]/text()')
            product_loader.add_xpath('sku', u'//span[@class="sku-code"]/text()')
            product_loader.add_value('identifier', identifier)
            product_loader.add_xpath('price', u'//span[@id="product_price"]/text()')
            if product_loader.get_output_value('price')<299:
                product_loader.add_value('shipping_cost', 15)

            product_loader.add_value('category', response.meta.get('category'))

            options = []
            names = {}
            for line in response.body.split('\n'):
                m = re.search('variants\[.*\] = \[\[([\d\.,]+),\d+,new Image.*\'([^\']+)\'', line)
                if m:
                    g = m.groups()
                    options.append([g[0], g[1], []])
                    continue
                m = re.search('variants\[.* = (.+);', line)
                if m:
                    g = m.groups()
                    options[-1][2].append(g[0])
                    continue
                m = re.search('names.*\[([^\]]+)\] = "(.+)";', line)
                if m:
                    g = m.groups()
                    names[g[0]] = g[1]
                    continue

            product_loader.add_xpath('brand', u'normalize-space(//div[contains(@class, "order-info")]/div/a/@title)')
            try:
                img = hxs.select('//img[@itemprop="image"]/@src').extract()[0]
                product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))
            except:
                pass

            product = product_loader.load_item()
            if options:
                for price, sku, ids in options:
                    prod = Product(product)
                    prod['name'] = prod['name'] + ' (' + ' '.join([names[id] for id in ids]) + ')'
                    prod['sku'] = sku
                    prod['identifier'] = prod['identifier'] + ':' + '.'.join(ids)
                    prod['price'] = Decimal(price)
                    if prod['price']<299:
                        prod['shipping_cost'] = 15
                    yield prod
            else:
                yield product
