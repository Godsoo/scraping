import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class KingJouetSpider(BaseSpider):
    name = 'legofrance-king-jouet.com'
    allowed_domains = ['king-jouet.com']
    start_urls = ('http://www.king-jouet.com/jeux-jouets/bdd-lego-duplo/page1.htm',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_urls = response.css('div.ResultList h2 a::attr(href)').extract()
        for url in product_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)
        
        next_page = response.xpath(u'//a[@rel="next"]/@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        
        loader = ProductLoader(item=Product(), response=response)
        identifier = response.url.split('/')[-1].split('-')[1]

        name = response.xpath(u'//h1/span/text()')[0].extract()

        sku = name.split('-')[0].strip()
        sku = sku if sku.isdigit() else ''

        category = response.xpath(u'//div[@id="ariane"]//a/text()').extract()
        category = category[-1].strip() if category else ''
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_css('brand', 'a.AvisResume::text')
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_css('price', 'span.price span.value-title::attr(title)')
        loader.add_value('price', 0)
        loader.add_css('image_url', 'div.galleryImg img::attr(src)')
        yield loader.load_item()
