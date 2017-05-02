import csv
import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class TedsSpider(BaseSpider):
    name = 'teds.com.au'
    allowed_domains = ['teds.com.au']
    start_urls = ['http://www.teds.com.au/brands/']
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        brands = hxs.select('//div[@role="main"]/ul/li/a')
        for brand in brands:
            name = brand.select('./text()').re(r'(.*) \(')
            url = brand.select('./@href').extract()[0].strip()
            yield Request(url + '?limit=all',
                          meta={'brand': name},
                          callback=self.parse_categories)


    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta.copy()
        categories = hxs.select('//div[@class="panel-heading" and contains(text(), "Category")]/following-sibling::ul[1]/li/a')

        for product in self.parse_products(response):
            yield product

        next_page = hxs.select('//a[@class="next"]/@href').extract()
        if next_page:
            yield(Request(next_page[0], meta=response.meta, callback=self.parse_categories))

        if 'category' not in response.meta and categories:
            for cat in categories:
                meta = response.meta.copy()
                meta['category'] = cat.select('./text()').extract().pop()
                url = cat.select('./@href').extract()[0].strip()
                yield Request(url, meta=meta,
                              callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response=response)
        products = response.xpath('//div[@class="product-list"]/div')
        for product in products:
            meta = response.meta.copy()
            url = product.select('./div/h4[@class="product-title"]/a/@href').extract().pop().strip()
            meta['name'] = product.select('./div/h4[@class="product-title"]/a/text()').extract()
            price = product.select('./div//span[@class="price"]/text()').extract()
            if price:
                meta['price'] = price.pop()
            else:
                continue

            meta['image_url'] = product.select('.//div[@class="product-img"]/a[not (contains(@class, "brand-logo"))]/img/@src').extract()

            yield Request(url, meta=meta, callback=self.parse_product)

        next_page = hxs.select('//div[@class="right-nav right"]/a/@href').extract()
        if next_page:
            url = next_page[0]
            yield Request(url, meta=response.meta, callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta.copy()

        identifier = hxs.select('//form[@id="product_addtocart_form"]'
                                '//input[@name="product"]/@value').extract().pop().strip()
        shipping_cost = hxs.select('//li[contains(string(), "Shipping cost:")]/span[@class="price"]/text()').extract()
        price = "".join(hxs.select('//span[@id="product-price-%s"]//text()' % identifier).extract()).strip()
        loader = ProductLoader(item=Product(), selector=response)
        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)
        loader.add_value('name', meta.get('name'))
        if price:
            loader.add_value('price', price)
        else:
            loader.add_value('price', meta.get('price'))
        if not loader.get_collected_values("price")[0]:
            return
        loader.add_value('url', response.url)
        loader.add_value('brand', meta.get('brand', ''))
        loader.add_value('category', meta.get('category', ''))
        if shipping_cost:
            loader.add_value('shipping_cost', shipping_cost.pop())
        loader.add_value('image_url', meta.get('image_url', ''))
        in_stock = bool(
            hxs.select('//form//div[@class="add-to-cart-btn"]/button[contains(string(), "Add to Cart")]') or
            hxs.select('//form//div[@class="add-to-cart-btn"]/button[contains(string(), "Coming Soon")]') or
            hxs.select('//form//div[@class="add-to-cart-btn"]/button[contains(string(), "Very Limited Stock!")]') or
            hxs.select('//form//div[@class="add-to-cart-btn"]/button[contains(string(), "Back Order Only")]')
        )
        if in_stock:
            loader.add_value('stock', 1)
        else:
            loader.add_value('stock', 0)

        yield loader.load_item()
