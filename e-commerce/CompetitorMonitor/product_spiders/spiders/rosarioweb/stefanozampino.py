import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price_eu

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

class StefanoZampinoSpider(BaseSpider):
    name = 'stefanozampino.it'
    allowed_domains = ['stefanozampino.it']
    start_urls = ['http://www.stefanozampino.it/index.php?route=information/sitemap']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="content"]/div[@class="middle"]//ul//a/@href').extract()

        for url in categories:
            yield Request(urljoin_rfc(base_url, url), self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_pages = hxs.select('//div[@class="pagination"]/div[@class="links"]/a/@href').extract()

        for url in next_pages:
            yield Request(urljoin_rfc(base_url, url), self.parse_products)

        products = hxs.select('//td[@class="list"]/a[1]/@href').extract()

        for url in products:
            yield Request(urljoin_rfc(base_url, url), self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', '//div[@id="content"]/div[@class="top"]/div[@class="center"]/h1/text()')
        product_loader.add_xpath('identifier', '//input[@name="product_id"]/@value')
        product_loader.add_xpath('sku', '//td/b[contains(text(), "Codice")]/../following-sibling::td/text()')
        product_loader.add_xpath('image_url', '//img[@id="image"]/@src')
        product_loader.add_xpath('brand', '//td/b[contains(text(), "Marca")]/../following-sibling::td/a/text()')
        product_loader.add_xpath('category', '//div[@id="breadcrumb"]/a[2]/text()')
        try:
            price = extract_price_eu(hxs.select('//td/b[contains(text(), "Prezzo")]/../following-sibling::td/span/text()').extract()[0])
        except:
            price = extract_price_eu(hxs.select('//td/b[contains(text(), "Prezzo")]/../following-sibling::td/strong/span/text()').extract()[1])
        product_loader.add_value('price', price)
        stock = hxs.select('//td/b[contains(text(), "Disponibilit")]/../following-sibling::td/text()').extract()
        if stock and not 'in magazzino' in stock:
            product_loader.add_value('stock', 0)

        yield product_loader.load_item()
