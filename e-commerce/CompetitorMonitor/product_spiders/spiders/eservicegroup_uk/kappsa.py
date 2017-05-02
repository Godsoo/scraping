# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class KappsaComUkSpider(BaseSpider):
    name = "kappsa.com_uk"
    allowed_domains = ["kappsa.com"]
    start_urls = ["http://www.kappsa.com/uk/"]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

#        category_urls =  hxs.select('//div[@class="header"]//a[@class="drop level-top"]/@href').extract()[1:-1]
        category_urls = hxs.select('//div[contains(@class, "col_1")]//@href').extract()
        basic_category_names = hxs.select('//div[@class="header"]//a[@class="drop level-top"]/span/text()').extract()[1:-1]
        for url in category_urls:
            yield Request(urljoin(base_url,url+"?limit=all&mode=list"), callback=self.parse_brands)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        brand_urls =  hxs.select('//*[@id="narrow-by-list"]/dd[1]//@href').extract()
        for url in brand_urls:
            yield Request(urljoin(base_url,url+"&limit=all&mode=list"), callback=self.parse_brands)
        parent_url = hxs.select('//div[@class="breadcrumbs"]/ul/li[2]/a/@href').extract()
        if parent_url:
            yield Request(urljoin(base_url, parent_url[0]+"?limit=all&mode=list"), callback=self.parse_brands)

    def parse_brands(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_urls = hxs.select('//ol[@id="products-list"]//h2[@class="product-name"]//@href').extract()
        for url in product_urls:
            if '/uk/' in url:
                yield Request(urljoin(base_url,url), callback=self.parse_product)

        parent_url = hxs.select('//div[@class="breadcrumbs"]/ul/li[2]/a/@href').extract()
        if parent_url:
            yield Request(urljoin(base_url, parent_url[0]+"?limit=all&mode=list"), callback=self.parse_brands)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())
        name = hxs.select('//*[@id="product_addtocart_form"]/div[3]/div[1]/h1/text()').extract()[0]
        loader.add_xpath('name', '//*[@id="product_addtocart_form"]/div[3]/div[1]/h1/text()')
        loader.add_value('url', response.url)
        price = hxs.select('//span[contains(@id, "product-price")]/span[@class="price"]/text()').extract()[-1][1:]
        loader.add_value('price', price)
        loader.add_value('shipping_cost', 0)
        loader.add_xpath('image_url', '//a[@id="zoom1"]/img/@src')
        loader.add_value('brand', name.split()[0])
        category = hxs.select('//li[contains(@class,"category")]//amasty_seo/text()').extract()[0].split()
        if len(category) <=2:
            category = category[0]
        elif category[2] == "Brand" or category[2] == "Device":
            category = "Accessories"
        else:
            category = category[2]
        loader.add_value('category', category)
        stock = hxs.select('//p[contains(text(), "Availability:")]/span/text()').extract()[0]
        if stock == "Out of stock":
            stock = 0
        else:
            stock = 1
        loader.add_value('stock', stock)
        loader.add_xpath('sku', '//*[@itemprop="sku"]/@content')
        loader.add_xpath('identifier', '//*[@itemprop="sku"]/@content')

        yield loader.load_item()

