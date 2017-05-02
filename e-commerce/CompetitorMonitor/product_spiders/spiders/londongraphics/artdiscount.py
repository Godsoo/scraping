# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider


class ArtDiscountSpider(BaseSpider):
    name = u'artdiscount.co.uk'
    allowed_domains = ['www.artdiscount.co.uk']
    start_urls = ('http://www.artdiscount.co.uk/all-products.html', )

    def __init__(self, *args, **kwargs):
        super(ArtDiscountSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_all_products, signals.spider_idle)
        self.get_brandless_products = 1

    def process_all_products(self, spider):
        if spider.name == self.name and self.get_brandless_products:
            self.get_brandless_products = 0
            self.log("Spider idle. Processing all products")
            r = Request('http://www.artdiscount.co.uk/all-products.html?limit=all',
                        callback=self.parse_products_list,
                        meta={'brand': ''})
            self._crawler.engine.crawl(r, self)
            raise DontCloseSpider

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brands = hxs.select('//*[@id="narrow-by-list"]/dd[2]/ol//li/a/text()').extract()
        urls = hxs.select('//*[@id="narrow-by-list"]/dd[2]/ol//li/a/@href').extract()
        for url, brand in zip(urls, brands):
            yield Request(urljoin_rfc(base_url, url + '&limit=all'), callback=self.parse_products_list, meta={'brand': brand})

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="category-products"]//h2/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        url = urljoin_rfc(base_url, response.url)
        image_url = hxs.select('//a[@class="zoom-link"]/@href').extract()
        options = hxs.select('//*[@id="super-product-table"]/tbody//tr[not(contains(td/text(), "No options"))]')
        if options:
            for option in options:
                loader = ProductLoader(item=Product(), selector=option)
                identifier = option.select('.//span[@class="regular-price"]/@id').extract()[0]
                identifier = identifier.replace('product-price-', '').strip()
                loader.add_value('identifier', identifier)
                name = option.select('.//h2/text()').extract()[0].strip()
                loader.add_value('url', url)
                loader.add_value('name', name)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                price = option.select('.//span[@class="regular-price"]/span/text()').extract()[0]
                price = extract_price(price.replace(u'\xa3', ''))
                loader.add_value('price', price)
                loader.add_value('sku', '')
                loader.add_value('brand', response.meta.get('brand'))
                loader.add_value('category', response.meta.get('brand'))
                stock = option.select('.//p[@class="availability out-of-stock"]')
                if stock:
                    loader.add_value('stock', 0)
                if price <= 34.99:
                    loader.add_value('shipping_cost', 4.50)
                else:
                    loader.add_value('shipping_cost', 0)
                yield loader.load_item()
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            name = hxs.select('//div[@class="product-shop"]/h1/text()').extract()[0].strip()
            loader.add_value('url', url)
            loader.add_value('name', name)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//div[@class="product-shop"]//span[@class="price"]/text()').extract()
            price = extract_price(price[0].replace(u'\xa3', '')) if price else 0
            loader.add_value('price', price)
            identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
            loader.add_value('identifier', identifier)
            loader.add_value('sku', '')
            loader.add_value('brand', response.meta.get('brand'))
            loader.add_value('category', response.meta.get('brand'))
            stock = hxs.select('//*[@id="product_addtocart_form"]//p[@class="availability out-of-stock"]')
            if stock:
                loader.add_value('stock', 0)
            if price < 34.99:
                loader.add_value('shipping_cost', 4.50)
            else:
                loader.add_value('shipping_cost', 0)
            yield loader.load_item()
