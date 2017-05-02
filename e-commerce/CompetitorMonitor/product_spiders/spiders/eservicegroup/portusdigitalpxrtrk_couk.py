# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request
from product_spiders.items import ProductLoader, Product
import urlparse

__author__ = 'Theophile R. <rotoudjimaye.theo@gmail.com>'


class PortusDigitalSpider(BaseSpider):
    name = "portusdigital-px.rtrk.co.uk"
    retry_http_codes = [500, 502, 503, 504, 400, 408, 404]
    allowed_domains = ["portusdigital-px.rtrk.co.uk"]
    start_urls = ["http://portusdigital-px.rtrk.co.uk"]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for href in hxs.select('//ul[@id="nav"]/li/a/@href').extract():
            yield Request(urlparse.urljoin(base_url, href) + "?limit=25&mode=list", callback=self.load_products)

    def load_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        nextp = hxs.select('//div[@class="pager"]//a[@class="next i-next"]')
        if nextp:
            href = nextp.select("./@href").extract()[0]
            yield Request(urlparse.urljoin(base_url, href), callback=self.load_products)

        product_category = hxs.select('//div[@class="page-title category-title"]/h1/text()').extract()
        if not product_category:
            self.log('ERROR Category not found!')
            product_category = ''
        else:
            product_category = product_category[0]

        for product_box in hxs.select('//ol[@id="products-list"]/li'):
            product_loader = ProductLoader(item=Product(), selector=product_box)
            product_loader.add_value('category', product_category)
            product_loader.add_xpath('name', './/h2[@class="product-name"]/a/text()')
            product_loader.add_xpath('url', './/h2[@class="product-name"]/a/@href')
            product_loader.add_xpath('price', './/span[@class="price"]/text()')
            product_loader.add_xpath('image_url', './/a[@class="product-image"]/img/@src')
            product_id = product_box.select('.//span[contains(@id,"product-price-")]/@id').re(r'(\d+)')
            if not product_id:
                self.log('ERROR: identifier not found!')
                return
            else:
                product_loader.add_value('identifier', product_id[0])
            yield product_loader.load_item()