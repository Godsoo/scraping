# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.utils import extract_price2uk, fix_spaces

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class ToysRUs(BaseSpider):
    name = "toysrus.ca"
    allowed_domains = ["toysrus.ca"]
    start_urls = ["http://www.toysrus.ca/category/index.jsp?categoryId=12480271"]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//dt[text()="Category"]//following-sibling::dd[1]//li/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        next_url = hxs.select('//ul[@class="pagination"]/li[@class="next"]/a/@href').extract()
        if next_url:
            yield Request(urljoin(base_url, next_url[0]), callback=self.parse_category)

        product_urls = hxs.select('//ul[contains(@class, "product-list")]//a[@class="title"]/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())

        brand = hxs.select('//label[@class="jda-brand-name"]/text()').extract()[0]
        brand = fix_spaces(brand)
        if brand.title() != 'Lego':
            return

        name = hxs.select('//div[@id="right-side"]//h1/text()').extract()[0]
        name = fix_spaces(name)
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        price = hxs.select('//div[@id="price"]//dd[@class="ours"]/text()').extract()
        if price:
            price = extract_price2uk(price[0])
            loader.add_value('price', price)

        img_url = hxs.select('//div[@id="bubble-wrapper"]//img/@src').extract()
        if img_url:
            loader.add_value('image_url', urljoin(base_url, img_url[0]))

        loader.add_value('category', 'Lego')
        loader.add_value('brand', 'Lego')

        stock = hxs.select('//*[@id="product-out-of-stock"]/a/img').extract()
        if stock:
            stock = 0
        else:
            stock = 1
        loader.add_value('stock', stock)

        loader.add_xpath('identifier', '//input[@name="productId_0"]/@value')

        if ')' in name:
            sku = name.split('(')[-1]
            sku = sku.split(')')[0]
            loader.add_value('sku', sku)

        yield loader.load_item()