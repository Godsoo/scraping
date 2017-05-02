import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import logging

HERE = os.path.abspath(os.path.dirname(__file__))

class BlushSpider(BaseSpider):
    name = 'cocopanda-blush.no'
    allowed_domains = ['blush.no']
    start_urls = ['https://www.blush.no/default.aspx']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@class="toplevel"]/li[not(@class="home")]/a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        url = response.url
        show_all = hxs.select('//a[contains(@id, "ShowAll")]/@href').extract()
        if show_all:
            url = urljoin_rfc(get_base_url(response), show_all[0])
        yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        category = hxs.select('//span[@class="SectionTitleText"]/text()').extract()
        products = hxs.select('//div[contains(@class, "productCell")]/div[@class="maininfo"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)

            try:
                brand = product.select("h3/a/text()").extract()[0]
            except IndexError:
                logging.error("No brand " + response.url)
                continue
            try:
                name = product.select("div[@class='shortDescription']/text()").extract()[0]
                if not name.strip():
                    name = product.select("div[@class='shortDescription']/a/text()").extract()[0]
            except IndexError:
                logging.error("No name " + response.url)
                continue
            loader.add_value('name', ' '.join((brand, name)))

            try:
                relative_url = product.select('h3/a/@href').extract()[0]
            except IndexError:
                logging.error("No url " + response.url)
                continue
            url = urljoin_rfc(get_base_url(response), relative_url)
            loader.add_value('url', url)

            identifier = url.split('/p-')[-1].split('-')[0]
            image_url = product.select('div[@class="image"]/a/img/@src').extract()[0]

            loader.add_xpath('brand', 'h3/a/text()')
            loader.add_value('category', category)
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url))
            loader.add_value('identifier', identifier)

            price = ''.join(product.select("div[@class='pricing']/span[@class='SalePrice1']/text()").re(r'[\d.,]+'))
            if not price:
                price = ''.join(product.select("div[@class='pricing']/span[@class='variantprice1']/text()").re(r'[\d.,]+'))
            if not price:
                logging.error("No price " + response.url)
                continue
            price = price.replace(' ', '').replace(".", "").replace(",", ".")

            loader.add_value('price', price)
            yield loader.load_item()
