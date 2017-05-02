# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider
from decimal import Decimal


class JacksonsartSpider(BaseSpider):

    name = u'jacksonsart.com'
    allowed_domains = ['www.jacksonsart.com']
    start_urls = ('http://www.jacksonsart.com/Brands-A-Z_All_Brands/c2200_1044/index.html', )


    def __init__(self, *args, **kwargs):
        super(JacksonsartSpider, self).__init__(*args, **kwargs)
        self.get_brandless_products = 1


    def process_all_products(self, spider):
        if spider.name == self.name and self.get_brandless_products:
            self.get_brandless_products = 0
            self.log("Spider idle. Processing all products")
            r = Request('http://www.jacksonsart.com/Art_Departments-A-Z_All_Departments/c2129_2128/index.html',
                        callback=self.parse_categories,
                        meta={'brand': ''})
            self._crawler.engine.crawl(r, self)
            raise DontCloseSpider


    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//ul[@id="menu"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url + '/show/all'), callback=self.parse_categories)

        urls = response.xpath('//div[@class="brand"]/a/@href').extract()
        brands = response.xpath('//div[@class="brand"]/a/img/@alt').extract()
        for url, brand in zip(urls, brands):
            yield Request(urljoin_rfc(base_url, url + '/show/all'), callback=self.parse_categories, meta={'brand': brand})


    def parse_categories(self, response):
        base_url = get_base_url(response)

        categories = response.xpath("//div[@class='breadcrumb']/a/text()").extract()
        urls = response.xpath('//td[@class="cat_list_title"]/a/@href').extract()
        urls += response.xpath('//div[@id="sidebar"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url + '/show/all'), callback=self.parse_categories, meta=response.meta)

        products = response.xpath('//ul[contains(@class, "products-grid")]/li[contains(@class, "item")]')
        if products:
            for product in products:
                full_range = product.xpath('.//a[contains(text(), "Full Range")]')
                if full_range:
                    continue
                name = product.xpath('.//h2[@class="product-name"]/text()').extract()
                if not name:
                    continue
                name = name[0]
                loader = ProductLoader(item=Product(), selector=product)
                loader.add_value('name', name)
                sku = product.xpath('.//div[@class="product-description"]/p[not(contains(text(), "Stock"))]/text()').extract()
                if not sku:
                    continue
                loader.add_value('sku', sku)
                loader.add_value('identifier', sku)
                url = product.xpath('.//a[@class="product-line"]/@href').extract()
                loader.add_value('url', url)
                image_url = product.xpath('.//div[@class="product-image"]/img/@src').extract()
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                brand = response.meta.get('brand', '')
                loader.add_value('brand', brand)
                out_of_stock = product.xpath('.//p[@class="availability out-of-stock"]').extract()
                if out_of_stock:
                    loader.add_value('stock', 0)
                price = product.xpath('.//span[@class="regular-price"]/span[@class="price"]/text()').extract()
                if not price:
                    price = product.xpath('.//p[@class="special-price"]/span[@class="price"]/text()').extract()
                if not price and out_of_stock:
                   continue
                price = extract_price(price[0])
                loader.add_value('price', price)
                yield loader.load_item()
