# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request

from product_spiders.items import ProductLoader, Product
from .kikkertland_dk import SpiderTemplate

import urlparse

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'



class VaabenShoppenSpider(SpiderTemplate):
    name = "vaabenshoppen.dk-2"
    allowed_domains = ["vaabenshoppen.dk"]
    start_urls = ["http://www.vaabenshoppen.dk/sitemap.aspx"]

    THOUSAND_SEP = "."
    DECIMAL_SEP = ","

    NAV_URL_EXCLUDE = ('/CustomerCreate.aspx', '/shoppingcart.aspx', '/atb.aspx') #, '/sitemap.aspx'

    PRODUCT_BOX_XOR = True

    #NAVIGATION = ['//table[@id="tblContent"]//td[@class="leftPane"]//a/@href', '//a/@href']
    NAVIGATION = ['//ul[@id="infoMenu1l0"]/li[6]/a/@href', '//div[@id="ShopContent"]//a/@href']

    PRODUCT_BOX = [('//div[@id="ShopContent"]//div[@class="plistAreaHeader"]/div//table[@class="Tabular"]/tbody/tr',
                    {'url': './td[2]/a/@href', 'name': './td[2]/a/text()', 'price': ['./td[4]/a/text()',]}),
                   ('//div[@id="ShopContent"]//div[@class="plistAreaHeader"]/div//div[@class="prelement"]',
                    {'url': './/div[@class="prmain"]/a[1]/@href', 'name': './/div[@class="prmain"]/a[1]/text()', 'price': ['.//div[@class="prbasket"]/p[@class="prpri"]/text()',]}),
                   ('//div[@id="ShopContent"]//div[@class="plistAreaHeader"]/div//div[@class="prbasket"]',
                    {'url': './a[1]/@href', 'name': './a[1]/text()', 'price': ['.//div[@class="prbasket"]/p/text()',]}),
                   ('.', {'name': './/div[@id="etHeading"]/table[@class="HeaderBarTables"]/tbody/tr[@class="HeaderBar"]/td[@class="etPname"]/h1[@class="HeaderBar"]/text()', 'price': ['.//div[@id="etHeading"]/table[@class="HeaderBarTables"]/tbody/tr[@class="HeaderBar"]/td[2]/text()', './/div[@id="etHeading"]/table[@class="HeaderBarTables"]/tbody/tr[@class="HeaderBar"]/td[3]/text()']})]

    #def parse(self, response):
    #    return self.parse2(response)

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        self.visited_urls = set()

        for href in hxs.select('//table[@id="tblContent"]//td[@class="leftPane"]//a/@href').extract():
            url = urlparse.urljoin(base_url, href)
            if url not in self.visited_urls:
                yield Request(url, callback=self.parse_products2)
                self.visited_urls.add(url)

    def parse_products2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for href in hxs.select('//table[@id="tblContent"]//td[@class="leftPane"]//a/@href').extract():
            url = urlparse.urljoin(base_url, href)
            if url not in self.visited_urls:
                yield Request(url, callback=self.parse_products2)
                self.visited_urls.add(url)

        for href in hxs.select('//ul[@id="pMenuSublevelsl1"]//a/@href').extract():
            url = urlparse.urljoin(base_url, href)
            if url not in self.visited_urls:
                yield Request(urlparse.urljoin(base_url, href), callback=self.parse_products2)
                self.visited_urls.add(url)

        for product_box in hxs.select('//div[@id="ShopContent"]//div[@class="plistAreaHeader"]/div'):

            tabular = product_box.select('.//table[@class="Tabular"]')
            if tabular:
                for pbox in tabular.select("./tbody/tr"):
                    product_loader = ProductLoader(item=Product(), selector=pbox)

                    product_loader.add_xpath('name', './td[2]/a/text()')
                    product_loader.add_value('url',  urlparse.urljoin(base_url, pbox.select('./td[2]/a/@href').extract()[0]))
                    product_loader.add_value('price', pbox.select('./td[4]/a/text()').extract()[0].split(" ")[-1].replace(".", "").replace(",", "."))
                    product = product_loader.load_item()
                    if product['url']: yield product
                continue

            elements = product_box.select('.//div[@class="prelement"]')
            if elements:
                for pbox in elements:
                    product_loader = ProductLoader(item=Product(), selector=pbox)

                    product_loader.add_xpath('name', './/div[@class="prmain"]/a[1]/text()')
                    product_loader.add_value('url', urlparse.urljoin(base_url, pbox.select('.//div[@class="prmain"]/a[1]/@href').extract()[0]))
                    product_loader.add_value('price', pbox.select('.//div[@class="prbasket"]/p[@class="prpri"]/text()').extract()[0].split(" ")[-1].replace(".", "").replace(",", "."))
                    product = product_loader.load_item()
                    if product['url']: yield product

            elif product_box.select('.//div[@class="prbasket"]'):
                product_loader = ProductLoader(item=Product(), selector=product_box)

                product_loader.add_xpath('name', './a[1]/text()')
                product_loader.add_value('url', urlparse.urljoin(base_url, product_box.select('./a[1]/@href').extract()[0]))
                product_loader.add_value('price', product_box.select('.//div[@class="prbasket"]/p/text()').extract()[0].split(" ")[-1].replace(".", "").replace(",", "."))
                product = product_loader.load_item()

                if product['url']: yield product
