# -*- coding: utf-8 -*-
import os
import re

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from utils import extract_price_eu as extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class LibrarieSpider(BaseSpider):
    name = 'elefant-librarie.net'
    allowed_domains = ['librarie.net']
    start_urls = ['http://www.librarie.net/carti']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//div[@class="small_menu"]/div/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url)

        products =  hxs.select('//div[@class="product_grid_text"]/a/@href').extract()
        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

        next = hxs.select('//div[@class="navbar"]/a[@title="PAGINA URMATOARE"]/@href').extract()
        if next:
            next = urljoin_rfc(get_base_url(response), next[0])
            yield Request(next)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@class="css_carte_titlu"]/h1/b/text()')
        loader.add_value('url', response.url)
        brand = hxs.select('//div[@class="produs_campuri" and b/text()="Editura:"]/a/text()').extract()
        loader.add_value('brand', brand)
        loader.add_value('category', 'Carti')
        sku = ''.join(hxs.select('//div[@class="produs_campuri" and b/text()="ISBN:"]/text()').extract()).strip()
        loader.add_value('sku', sku)
        loader.add_value('identifier', re.findall('p/(.*)/', response.url)[0])
        image_url = hxs.select('//a[@rel="thumbnail"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        price = ''.join(hxs.select('//tr[contains(td/b/text(), "ul nostru:")]/td/b[@class="red"]/text()').extract()).strip()
        if not price:
            price = ''.join(hxs.select('//tr[td/b/text()="Pret:"]/td/text()').extract()).strip()

        loader.add_value('price', extract_price(price))

        out_of_stock = 'IN STOC' not in ''.join(hxs.select('//tr[td/b/text()="Disponibilitate:"]/td/text()').extract()).strip().upper()
        if out_of_stock:
            loader.add_value('stock', 0)

        if loader.get_output_value('price') < 150:
            loader.add_value('shipping_cost', 11.99)
        
        yield loader.load_item()
