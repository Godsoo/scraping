# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from product_spiders.items import Product, ProductLoader
from decimal import Decimal

import logging

class EuroprezziItSpider(BaseSpider):
    name = "europrezzi.it"
    allowed_domains = ["europrezzi.it"]
    start_urls = (
        # 'http://www.europrezzi.it/',
        'http://www.europrezzi.it/climatizzazione',
        'http://www.europrezzi.it/riscaldamento',
        'http://www.europrezzi.it/per-il-bagno/rubinetteria',
        'http://www.europrezzi.it/per-il-bagno/termoidraulica',
        'http://www.europrezzi.it/per-il-bagno/trituratori-sanitari',
        )

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories = hxs.select("//div[@id='box_left_ctl02_livello_box']//table[@class='tabellaMenu']/tr/td[2]/a/@href").extract()
        # for category in categories:
            # yield Request(category, callback=self.parse)
        pages = hxs.select("//div[@class='pages']/ol/li/a/@href").extract()
        for page in pages:
            yield Request(page, callback=self.parse)
        items = hxs.select("//div[contains(@class, 'item')]/a[contains(@class, 'product-image')]/@href").extract()
        for item in items:
            yield Request(item, callback=self.parse_item)

    def parse_item(self, response):
        url = response.url

        hxs = HtmlXPathSelector(response)
        name = hxs.select("//div[@class='product-name']/h1/text()").extract()
        if not name:
            logging.error("NO NAME! %s" % url)
            return
        name = name[0]

        # adding product
        price = hxs.select("//div[@class='price-box']//span[@class='price']/text()").re(u'\u20ac\xa0(.*)')
        if not price:
            logging.error("NO PRICE! %s" % url)
            return
        price = price[0].replace(".", "").replace(",", ".")

        # price_delivery = hxs.select("//div[@class='product-shop']/\
            # text()[(preceding::div[@class='price-box']) and (following::div[@class='add-to-holder'])]"
        # ).re(u'€\xa0([\d,.]*)')
        # if not price_delivery:
            # logging.error("NO PRICE DELIVERY! %s" % url)
            # return
        # price_delivery = price_delivery[0].replace(".", "").replace(",", ".")
        # if Decimal(price) > 0:
            # price = Decimal(price) + Decimal(price_delivery)

        identifier = hxs.select('//form[@id="product_addtocart_form"]/div/input[@name="product"]/@value').extract()

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        yield l.load_item()
