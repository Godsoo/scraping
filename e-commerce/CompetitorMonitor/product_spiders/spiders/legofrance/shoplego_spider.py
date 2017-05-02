import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from product_spiders.utils import extract_price_eu as extract_price

from scrapy import log
import logging

class ShopLegoSpider(BaseSpider):
    name = 'legofrance-shop.lego.com'
    allowed_domains = ['shop.lego.com', 'lego.com']
    start_urls = ['http://search-fr.lego.com/?q=&cc=FR']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        URL_BASE = get_base_url(response)

        products = hxs.select('//ul[@id="product-results"]/li')
        for product in products:        
            l = ProductLoader(item=Product(), selector=product)
            name = product.select('h4/a/@title').extract()[0].replace('<i>', '').replace('</i>', '')
            if not name:
                continue
            l.add_value('name', name)
            url = urljoin_rfc(URL_BASE, product.select('h4/a/@href').extract()[0])
            l.add_value('url', url)
            identifier = product.select('h4/span[@class="item-code"]/text()').extract()
            if not identifier:
                continue
            l.add_value('identifier', identifier[0])
            l.add_xpath('sku', 'h4/span[@class="item-code"]/text()')
            #price = product.select('ul/li/em/text()').extract()
            #if price:
            #    price = price[0].replace(',', '.')
            #l.add_value('price', price)
            l.add_value('brand', 'LEGO')
            l.add_value('category', '')
            l.add_xpath('image_url', 'a/img/@src')
            prod = l.load_item()
            yield Request(url, callback=self.parse_product, meta={'product': prod})       
        next = hxs.select('//span[@class="view_next"]/a/@href').extract()
        if next:
            yield Request(urljoin_rfc(URL_BASE, next[0]))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        URL_BASE = get_base_url(response)
        if "/en-US/" in response.url:
            return
        product = response.meta.get('product', Product())
        category = hxs.select('//a[@id="categoryBrandIcon"]/img/@title').extract()
        if category:
            product['category'] = category[0]
        price = hxs.select('//span[contains(@class, "product-sale-price")]/em/text()').extract()
        if not price:
            price = hxs.select('//span[contains(@class, "product-price")]/em/text()').extract()
        price = price[0] if price else '0'
        product['price'] = extract_price(price)
        yield product
