# -*- coding: utf-8 -*-

import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request

import urlparse

from product_spiders.items import ProductLoader, Product

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'

class EventstadMusikkSpider(BaseSpider):
    name = "evenstadmusikk.no"
    allowed_domains = ["evenstadmusikk.no"]
    start_urls = ('http://evenstadmusikk.no/index.php',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        self.navig_url_set = set()

        cat_urls = hxs.select('//div[@id="top_nav"]//a/@href').extract()
        for cat_url in cat_urls:
            subcat_url = urlparse.urljoin(base_url, cat_url)
            self.navig_url_set.add(subcat_url)
            yield Request(subcat_url, callback=self.browse_and_parse)

    def browse_and_parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for subcat_href in hxs.select('//div[@id="navColumnOne"]//a/@href').extract():
            subsubcat_url = urlparse.urljoin(base_url, subcat_href)
            if subsubcat_url not in self.navig_url_set:
                self.navig_url_set.add(subsubcat_url)
                yield Request(subsubcat_url, callback=self.browse_and_parse)

        pages = hxs.select('//div[@id="newProductsDefaultListingTopLinks"]//a/@href').extract()
        for url in pages:
            yield Request(url, callback=self.browse_and_parse)

        # parse product listing in this page, if any
        for product in hxs.select('//table[@class="table-product-attributes"]'):
            product_loader = ProductLoader(item=Product(), response=response)
            url = product.select('.//td[@class="main"]/a/@href').extract()[0]
            product_loader.add_value('identifier', re.search(r'products_id=(\d+)', url).groups()[0])
            product_loader.add_value('url', url)
            product_loader.add_value('name', product.select('.//td[@class="main"]/a/strong/text()').extract()[0])
            try:
                price = product.select('.//span[@class="table-price"]/text()')\
                    .extract()[0].split("-")[0].split(" ")[1].replace('.', '').replace(',', '.')
            except:
                price = product.select('.//span[@class="productSpecialPrice"]/text()')\
                    .extract()[0].split("-")[0].split(" ")[1].replace('.', '').replace(',', '.')
            product_loader.add_value('price', price)

            yield product_loader.load_item()

        # edge case: product listing page with a single product
        product_price = hxs.select('//h2[@id="productPrices"]/text()').extract()
        if product_price:
            # this product listing page contains a single product
            product_loader = ProductLoader(item=Product(), response=response)

            product_loader.add_xpath('name', '//h1[@id="productName"]/text()')
            product_loader.add_value('url', response.url)
            product_loader.add_value('identifier', re.search(r'products_id=(\d+)', response.url).groups()[0])
            try:
                product_loader.add_value('price',
                                         product_price[0].split("-")[0]\
                                         .split(" ")[1].replace('.', '').replace(',', '.'))
            except:
                product_loader.add_value('price',
                                         hxs.select('//span[@class="productSpecialPrice"]/text()').extract()[0]\
                                         .split("-")[0].split(" ")[1].replace('.', '').replace(',', '.'))

            yield product_loader.load_item()
