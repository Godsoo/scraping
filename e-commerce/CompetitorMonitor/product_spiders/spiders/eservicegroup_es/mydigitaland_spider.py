# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import extract_price_eu, extract_price2uk


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class MyDigitaLandSpider(BaseSpider):
    name = "eservice-es-mydigitaland.com"
    allowed_domains = ["es.mydigitaland.com"]
    start_urls = ["http://es.mydigitaland.com/"]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//ul[@id="nav"]/li//li[contains(@class, "nav-item")]/a/@href').extract()
        category_urls += hxs.select('//ul[@id="nav"]/li/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin(base_url, url))

        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

        next = hxs.select('//li[@class="next"]/a/@href').extract()
        if next:
            yield Request(urljoin(base_url, next[0]))

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())
        name = hxs.select('//h3[@itemprop="name"]/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        price = ''.join(hxs.select('//div[contains(@class, "product-primary-column")]//p[@class="special-price"]/span[@class="price"]/text()').extract()[0].split())
        price = extract_price_eu(price)
        loader.add_value('price', price)
        loader.add_value('shipping_cost', 0)
        image_url = hxs.select('//img[@id="image-main"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(base_url, image_url[0]))
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li[contains(@class, "category")]/a/span/text()').extract()
        loader.add_value('category', category)
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        in_stock = hxs.select('//p[contains(@class, "availability")]/span[text()="En existencia"]')
        if not in_stock:
            loader.add_value('stock', 0)
        identifier = hxs.select('//meta[@itemprop="productID"]/@content').re(':(.*)')[0]
        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)

        yield loader.load_item()

