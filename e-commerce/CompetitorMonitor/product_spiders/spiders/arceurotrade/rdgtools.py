import os
import logging
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class RDGToolsSpider(BaseSpider):
    name = 'rdgtools.co.uk_arceurotrade'
    allowed_domains = ['rdgtools.co.uk', 'www.rdgtools.co.uk']
    start_urls = (u'http://www.rdgtools.co.uk/acatalog/sitemap.html', )

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        categories = hxs.select(u'//div[@id="content"]//li/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        for product in self.parse_product(response):
            yield product

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select(u'//td[child::a[child::b]]')
        products += hxs.select(u'//td[child::div[@class="content_right" and child::a[child::b]]]')
        for product in products:
            name = product.select(u'.//a/b/text()')[0].extract().split()
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            price = product.select(u'.//text()').re(u'\xa3([\d\.,]+) Including VAT')
            multiplier = Decimal("1")
            if not price:
                multiplier = Decimal("1")
                price = product.select(u'.//b/*/text()').re(u'\xa3([\d\.,]+) Including VAT')
            if not price:
                multiplier = Decimal("1.2")
                price = product.select(u'.//text()').re(u'Price: \xa3([\d\.,]+)')
            if not price:
                multiplier = Decimal("1.2")
                price = product.select(u'.//b/*/text()').re(u'\xa3([\d\.,]+)')
            if price:
                price = Decimal(price[0].replace(",", "")) * multiplier
            else:
                continue
            loader.add_value('price', price)

            image_url = product.select(u'../td[1]//img/@src').extract()
            if image_url:
                image_url = urljoin_rfc(get_base_url(response), image_url[0])
                loader.add_value('image_url', image_url)

            sku = product.select("./text()[1]").re(r"Ref: (.+)$")
            if not sku:
                logging.error("No SKU!!! %s, %s" % (response.url, loader.get_output_value('name')))
                continue
            sku = sku[0]
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)

            # if loader.get_output_value('price'):
            yield loader.load_item()

        products = hxs.select(u'//div[@class="product_list"]')
        for product in products:
            name = product.select(u'.//h3[@class="product"]/text()')[0].extract().split()
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            price = product.select(u'.//h3[@class="product_price"]//text()').re(u'\xa3([\d\.,]+) Including VAT')
            multiplier = Decimal("1")
            if not price:
                multiplier = Decimal("1")
                price = product.select(u'.//b/*/text()').re(u'\xa3([\d\.,]+) Including VAT')
            if not price:
                multiplier = Decimal("1.2")
                price = product.select(u'.//h3[@class="product_price"]//text()').re(u'Price: \xa3([\d\.,]+)')
            if not price:
                multiplier = Decimal("1.2")
                price = product.select(u'.//b/*/text()').re(u'\xa3([\d\.,]+)')
            if price:
                # price = price[0]
                price = Decimal(price[0].replace(",", "")) * multiplier
            else:
                continue
            loader.add_value('price', price)

            image_url = product.select(u'.//div[@class="image_product"]//img/@src').extract()
            if image_url:
                image_url = urljoin_rfc(get_base_url(response), image_url[0])
                loader.add_value('image_url', image_url)

            sku = product.select(u'.//div[preceding-sibling::div[@class="image_product"]]/p[1]/text()').re(r"Ref: (.+)$")
            if not sku:
                logging.error("No SKU!!! %s, %s" % (response.url, loader.get_output_value('name')))
                continue
            sku = sku[0]
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)

            # if loader.get_output_value('price'):
            yield loader.load_item()
