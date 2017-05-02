# -*- coding: utf-8 -*-
import re
import json
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class MattressManSpider(BaseSpider):
    name = "colourbank-mattressman.co.uk"
    allowed_domains = ('mattressman.co.uk', )
    start_urls = ('http://www.mattressman.co.uk/', )

    def _start_requests(self):
        yield Request('http://www.mattressman.co.uk/handlers/JSON.ashx?req=Product&ProductID=46437', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//div[@id="slidemenu"]/ul/li/a'):
            for url in cat.select('..//a/@href').extract():
                yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta={'category': ''.join(cat.select('./text()').extract())})

    def parse_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@id="ctl00_ctl00_body_stdBody_landingPageTypes"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta=response.meta)
        for url in hxs.select('//div[@id="ctl00_ctl00_body_stdBody_productTypes"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_list, meta=response.meta)
        found = False
        for id in hxs.select('//div[contains(@class,"product-list-item")]//div[@id]/@id').extract():
            try:
                _ = int(id)
                found = True
                yield Request('http://www.mattressman.co.uk/handlers/JSON.ashx?req=Product&ProductID=' + id, callback=self.parse_product, meta=response.meta)
            except:
                pass
        if not found:
            self.log('No products on %s' % response.url)


    def parse_product(self, response):
        data = json.loads(response.body)

        def html_expand(s):
            return s.replace('&#34;', '"')

        product = Product()
        product['sku'] = data['id']
        product['identifier'] = data['id']
        product['name'] = html_expand(data['name'])
        product['brand'] = data['manufacturer']['name']
        product['category'] = response.meta['category']
        found = False
        for opt in data['variations']:
            prod = Product(product)
            prod['identifier'] = opt['id']
            prod['name'] = html_expand(opt['name'])
            prod['url'] = urljoin_rfc(get_base_url(response), opt['url'])
            prod['price'] = extract_price(opt['price'])
            prod['stock'] = opt['stock']
            prod['image_url'] = urljoin_rfc(get_base_url(response), opt.get('images800', opt.get('images500'))[0].get('src'))
            found = True
            yield prod
        if not found:
            self.log('Options not found on %s' % (response.url))
            yield product

