import os
import csv
import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider
from scrapy import signals

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import logging
HERE = os.path.abspath(os.path.dirname(__file__))


class NotebooksbilligerSpider(BaseSpider):
    name = 'notebooksbilliger.de'
    allowed_domains = ['notebooksbilliger.de', 'epoq.de']
    start_urls = ('http://search.epoq.de/inbound-servletapi/getSearchResult?tenantId=notebooksbilliger&format=json&query=Logitech&sessionId=33200879ec55bfaf361c321aa26fca8c&orderBy=&order=desc&locakey=&style=onlyId&full&callback=jQuery18207697459660112135_1406576132684&&limit=1000&offset=0&_=1406576135344',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('sku', 'mpn'), ('sku', 'ean13')]
    items = {}

    def __init__(self, *a, **kw):
        super(NotebooksbilligerSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if spider != self: return
        if self.items:
            self.crawler.engine.schedule(Request('http://' + self.allowed_domains[0], callback=self.yield_product, dont_filter=True), spider)
            raise DontCloseSpider('Found pending requests')

    def yield_product(self, response):
        for item in self.items.values():
            yield item.load_item()
        self.items = None

    def _start_requests(self):
        yield Request('http://www.notebooksbilliger.de/logitech+k830+illuminated+living+room+keyboard/eqsqid/dc034145-ba5e-417d-b751-99748adbb8b8', meta={'product':Product()}, callback=self.parse_product)

    def parse(self, response):
        b = response.body
        data = json.loads(b[b.index('(') + 1:b.rindex(')')])

        ids = [r['match-item']['@node_ref'] for r in data['result']['findings']['finding']]

        for i in xrange(0, len(ids), 50):
            yield Request('http://www.notebooksbilliger.de/extensions/ntbde/getsearchlisting.php?pids=' + ','.join(ids[i:i + 50]), callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//div[@class="mouseover clearfix"]'):
            product = Product()
            product['price'] = extract_price_eu(''.join(productxs.select('.//span[@class="product_price_listing"]//text()').extract()))
            if product['price'] == 0:
                product['stock'] = '0'
            else:
                product['stock'] = '1'

            url = urljoin_rfc(get_base_url(response), productxs.select('.//a[@class="product_link"]/@href').extract()[0])
            yield Request(url, callback=self.parse_product, meta={'product': product})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        identifier = hxs.select('substring-after(//span[@itemprop="identifier"]/@content,":")').extract().pop()
        loader = ProductLoader(item=response.meta['product'], selector=hxs)
        loader.add_value('identifier', identifier)

        loader.add_xpath('sku', '//span[contains(text(),"Herstellernummer:")]/span/text()')
        price = hxs.select('//span[@id="product_price_detail"]/span[@itemprop="price"]/text()').extract()
        price = price[0] if price else 0
        loader.add_value('price', extract_price_eu(price))
        if price == 0:
            loader.add_value('stock', '0')
        else:
            loader.add_value('stock', '1')

        if not loader.get_output_value('sku'):
            loader.add_xpath('sku', 'substring-after(//span[@itemprop="identifier"]/@content,":")')
            loader.add_value('brand', 'Logitech')

        loader.add_value('url', response.url)
        name = hxs.select('//*[@itemprop="name"]//text()').extract().pop()
        loader.add_value('name', name)
        if not loader.get_output_value('brand') and 'logitech' in name.lower():
            loader.add_value('brand', "Logitech")

        loader.add_xpath('category', '//div[@id="path_text"]/div[position()=last()]//span/text()')

        img = hxs.select('//img[@id="detailimage"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        loader.add_value('shipping_cost', extract_price_eu(''.join(hxs.select('//a[contains(@onclick,"Versandkosten Info")]/../text()').extract()).split(' ab ')[-1]))
        if identifier in self.items:
            old_price = self.items[identifier].get_collected_values("price")[0]
            if old_price < extract_price_eu(price):
                return
        self.items[identifier] = loader
        #yield loader.load_item()
