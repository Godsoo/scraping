import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser
from product_spiders.utils import extract_price

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class TermoIdraulicaOnlineSpider(BaseSpider):
    name = 'newbricoman-termoidraulicaonline.it'
    allowed_domains = ['termoidraulicaonline.it']
    start_urls = ('http://www.termoidraulicaonline.it',)

    def parse(self, response):
        #hxs = HtmlXPathSelector(response)
        yield FormRequest(url="http://www.termoidraulicaonline.it/ricerca.php",
                            formdata={'ricerca': ''},
                            callback=self.parse_search)
        '''
        categories = hxs.select('//a[@class="testo14-titolo"]/@href').extract()
        pages = hxs.select('//a[@class="cmdSetPage_tblProdotti_frontend_paginator"]/@href').extract()
        if len(pages) > 1:
            pages = pages[1:]
            base_cat = '/'.join(response.url.split('/')[:-1])
            for page in pages:
                categories.append(urljoin_rfc(base_cat, page))

        for cat in categories:
            yield Request(cat)
        '''

    def parse_search(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//strong[text()="Scheda prodotto"]/../@href').extract()
        for p in products:
            yield Request(urljoin_rfc(base_url, p), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', '//span[@class="testo16-titolo"]/text()')
        loader.add_xpath('sku', '//span[@id="shownIntxt"]/text()')
        price = hxs.select('//span[@class="titolo-cat"]/text()') or 0
        if price:
            price = price.extract()[0].split()[1]
        if price==0:
            log.msg('ERROR: No price url: ' + response.url)
            return
        loader.add_value('price', price)
        category = hxs.select('//div[@class="testo11-nero"]/strong/text()').extract()[-1]
        loader.add_value('category', category)
        loader.add_xpath('image_url', '//a[@id="foto_visualizzata_link"]/img/@src')
        loader.add_value('identifier', hxs.select('//meta[@property="og:url"]/@content').extract()[0].split('/')[4])
        loader.add_value('url', response.url)
        yield loader.load_item()
