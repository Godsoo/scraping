from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoader
from decimal import Decimal

import logging
import json


class ConvienesempreItSpider(BaseSpider):
    name = "convienesempre.it"
    allowed_domains = ["convienesempre.it"]

    start_urls = (
        'http://www.convienesempre.it/',
        )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//ul[@class="em-catalog-navigation"]/li/a/@href').extract()
        for url in urls:
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        '''
        categories = hxs.select("//ul[@id='nav']//a/@href").extract()
        for category in categories:
            yield Request(category, callback=self.parse)
        '''
        pages = hxs.select("//div[@class='pages']/ol/li/a/@href").extract()
        for page in pages:
            yield Request(page, callback=self.parse_category)


        items = hxs.select('//li[contains(@class, "item")]/div')
        for item in items:
            name = item.select("h2[@class='product-name']/a/text()").extract()
            if not name:
                logging.error("NO NAME! %s" % response.url)
                return
            name = name[0]

            url = item.select("h2[@class='product-name']/a/@href").extract()
            if not url:
                logging.error("NO URL! %s" % response.url)
                return
            url = url[0]

            # adding product
            price = item.select("div[@class='price-box']/p[@class='special-price']/span[@class='price']/text() |\
                                 div[@class='price-box']/span[@class='regular-price']/span[@class='price']/text()"
            ).extract()
            if not price:
                logging.error("NO PRICE! %s" % response.url)
                return
            price = price[0].replace(".", "").replace(",", ".")

            identifier = item.select('.//*[contains(@id, "product-price-")]/@id').re(r'product-price-(\d+)')

            l = ProductLoader(item=Product(), response=response)
            l.add_value('identifier', identifier)
            l.add_value('name', name)
            l.add_value('url', url)
            l.add_xpath('image_url', 'a[@class="product-image"]/img/@src')
            l.add_xpath('category', '//div[contains(@class, "category-title")]/h1/text()')
            l.add_value('price', price)
            yield l.load_item()
