# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from utils import extract_price_eu

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class SFeraUfficio(BaseSpider):
    name = "futek.it"
    allowed_domains = ["futek.it"]
    start_urls = ["http://www.futek.it"]

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//ul[@id="categoriesBoxes"]/li/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_category)



    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_urls = hxs.select('//div[@id="mainResultBox"]//h2/a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

        next_url = hxs.select('//a[contains(text(), "Avanti")]/@href').extract()
        if next_url != []:
            yield Request(urljoin(base_url, next_url[0]), callback=self.parse_category)

        category_urls = hxs.select('//ul[@id="categoriesBoxes"]/li/a/@href').extract()
        for url in category_urls:
            yield Request(urljoin(base_url, url), callback = self.parse_category)


    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())



        loader.add_xpath('name','//div[@id="sheetBoxTopDetails"]//h1/span/text()' )
        loader.add_value('url', response.url)

        price = hxs.select('//h3/span[@id="md_price"]/text()').extract()
        if price == []:
            price = 0
        else:
            price = extract_price_eu(price[0])
        loader.add_value('price', price)

        loader.add_value('shipping_cost', 0)
        image_url = hxs.select('//img[@id="sheetMainImage"]/@src').extract()[0]
        loader.add_value('image_url', urljoin(base_url, image_url))

        category = hxs.select('//div[@id="breadcrumbs"]/span[@id="md_category"]/a/text()').extract()
        try:
            category.remove('Home')
        except ValueError:
            pass
        category = ' > '.join(category)
        loader.add_value('category', category)

        loader.add_xpath('brand', '//td[@id="md_brand"]/text()')

        stock = hxs.select('//span[@id="md_availability"]/@content').extract()[0]
        if stock == 'out_of_stock':
            stock = 0
        else:
            stock = 1
        loader.add_value('stock', stock)


        loader.add_xpath('sku', '//td[@id="md_mpn"]/text()')
        loader.add_xpath('identifier', '//div[@id="sheetBoxTopDetails"]//tr[@class="code"]/td/text()')


        yield loader.load_item()


