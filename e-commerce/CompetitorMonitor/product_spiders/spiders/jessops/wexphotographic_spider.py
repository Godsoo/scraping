import re
import json
import os
import csv
import paramiko

import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.item import Item, Field

from jessopsitem import JessopsMeta

from product_spiders.utils import extract_price

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class WexPhotographicSpider(BaseSpider):
    name = 'jessops-wexphotographic.com'
    allowed_domains = ['wexphotographic.com']

    start_urls = ['http://www.wexphotographic.com']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="navmain"]//a[not(contains(@href, "used"))]/@href').extract()
        categories += hxs.select('//div[@id="navhome"]//a/@href').extract()
        categories += hxs.select('//div[@class="curvesBox"]//a/@href').extract()
        for category in categories: 
            yield Request(urljoin_rfc(get_base_url(response), category))

        products = hxs.select('//ul[@id="productList"]//h2/a[not(contains(@href, "buy-used"))]/@href').extract()
        for product in products: 
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

        next = hxs.select('//div[@id="pages"]//a[contains(text(), "Next")]/@href').extract()
        if next:
            yield Request(urljoin_rfc(get_base_url(response), next[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('identifier', '//input[@id="ctl00_pnlMainContent_hdnLPMainProductSKU"]/@value')
        sku = ''.join(hxs.select('//b[@property="gr:hasMPN"]/text()').extract()).strip()
        loader.add_value('sku', sku)
        categories = hxs.select('//div[@id="navbc"]//span/a/text()').extract()[1:]
        loader.add_value('brand', categories[-1])
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h1[@property="gr:name"]/text()')
        price = hxs.select('//span[@property="gr:hasCurrencyValue"]/text()').extract()[0]
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        image_url = hxs.select('//div[@id="mainimage"]/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//img[@class="topimage"]/@src').extract()
        image_url = urljoin_rfc(get_base_url(response), image_url[0].strip()) if image_url else ''
        loader.add_value('image_url', image_url)

        if loader.get_output_value('price')<50:
            loader.add_value('shipping_cost', 2.99)

        out_of_stock = hxs.select('//span[@typeof="gr:QuantitativeValue"]/span[contains(text(), "Awaiting")]')
        if out_of_stock:
            loader.add_value('stock', 0)
        product = loader.load_item()

        metadata = JessopsMeta()
        cashback = hxs.select('//div[@class="cashback" and a[contains(text(), "Cashback")]]/a/text()').re('(.*) Cashback')
        cashback = cashback[0] if cashback else ''
        metadata['cashback'] = cashback

        finance =  hxs.select('//a[contains(@href, "finance")]/span//text()').extract()
        if finance:
            payment = round(product['price'] / extract_price(finance[0]), 2)
            finance = ' '.join(''.join(hxs.select('//a[contains(@href, "finance")]//text()').extract()).split())
            finance_payments = re.findall("<p class='ifc-text'>(.*)</p>", response.body)
            if finance_payments:
                finance_payments = finance_payments[0].replace('"+DCP(fpayments1)+"', str(payment)).replace('<br />', '').replace(u'&pound;',u'\u00a3')
                finance = finance + ' ' + finance_payments
        else:
            finance = ''

        metadata['finance'] = finance
        product['metadata'] = metadata

        yield product
