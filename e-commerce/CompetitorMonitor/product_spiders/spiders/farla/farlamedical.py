# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
import urllib
from product_spiders.items import Product, ProductLoader
import os
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class FarlamedicalSpider(BaseSpider):
    name = u'farlamedical.co.uk'
    allowed_domains = ['www.farlamedical.co.uk']
    start_urls = [
        u'http://www.farlamedical.co.uk/',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="main-nav"]//li[not(contains(a/span/text(), "Pharmaceuticals") or contains(a/span/text(), "Services") or contains(a/span/text (), "Stationery"))]//li//a/@href').extract()
        categories += hxs.select('//div[@id="main-nav"]//li[not(contains(a/span/text(), "Pharmaceuticals") or contains(a/span/text(), "Services") or contains(a/span/text (), "Stationery"))]//h2//a/@href').extract()
        categories += hxs.select('//div[contains(@class, "producttabs")]//a[contains(@href, "category")]/@href').extract()
        categories += hxs.select('//div[@class="product category"]//h3/a/@href').extract()

        for category in categories:
            yield Request(urljoin_rfc(get_base_url(response), category)+'page_all/')

        products = hxs.select('//div[@class="product"]/div/h3/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        search_code = response.meta.get('search_code')
        #if search_code in self.found_codes:
        #    return
        not_found = hxs.select('//*[@id="ctl00_cphMainBlock_pnlSubCategory"]/p/text()').extract()
        if not_found and not_found[0].strip() == 'Products not found':
            return
        image_url = hxs.select('//*[@id="wrap"]//img[@itemprop="image"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        categories = hxs.select('//div[@class="path"]/a/text()').extract()
        categories = categories[1:] if categories else []
        brand = hxs.select('//span[@itemprop="name"]/text()').extract()
        brand = brand[0] if brand else ''
        products = hxs.select('//div[@class="productoptions"]//div[@class="product"]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_value('url', response.url)
            name = product.select('.//h3/text()').extract()[0].strip()
            loader.add_value('name', name)
            loader.add_value('image_url', image_url)
            for category in categories:
                loader.add_value('category', category)
            loader.add_value('brand', brand)
            sku = product.select('.//span[@class="info"]/text()').extract()[0].strip()
            price = product.select('.//div[@class="offers"]//span[@class="newprice"]/text()').extract()
            if not price:
                price = product.select('.//div[@class="price"]//div[@class="current"]/text()').extract()
            price = price[0].strip() if price else '0'
            price = extract_price(price)
            loader.add_value('price', price)
            loader.add_value('sku', sku)
            identifier = sku
            loader.add_value('identifier', identifier.strip())
            if int(price) <= 100:
                loader.add_value('shipping_cost', 6.6)
            #self.found_codes.append(sku)
            yield loader.load_item()
