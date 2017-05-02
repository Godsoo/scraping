import csv
import os
import copy
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class ToysRUsSpider(BaseSpider):
    name = 'legofrance-toysrus.fr'
    allowed_domains = ['toysrus.fr']
    start_urls = ('http://www.toysrus.fr/category/index.jsp?categoryId=5095281&ab=Accueil_marque_Lego',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category_urls = hxs.select(u'//div[@class="featured-category-box"]/div[@class="top"]/a/@href').extract()
        for url in category_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        product_urls = hxs.select(u'//ul[contains(@class,"product-list")]//a[@class="title"]/@href').extract()
        for url in product_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

        next_page = hxs.select(u'//li[@class="next"]/a/@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)

        if 'productId=' in response.url:
            yield Request(response.url, callback=self.parse_product, dont_filter=True)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        identifier = re.search('productId=([\d]+)', response.url).group(1)

        sku = hxs.select(u'//dt[contains(text(),"Fabricant #")]/following-sibling::dd[1]/text()').extract()
        sku = sku[0] if sku else ''

        category = hxs.select(u'//a[@class="breadcrumb"]/text()').extract()
        category = category[-1].strip() if category else ''
        loader.add_value('identifier', identifier)
        loader.add_xpath('name', u'//div[@id="right-side"]/div[@id="price-review-age"]/h1/text()')
        brand = hxs.select(u'//label[@class="jda-brand-name"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price =  hxs.select(u'//div[@id="price"]//dl[@class="price"]/dd[@class="ours"]/text()').extract()
        price = price[0].replace(',', '.') if price else ''
        loader.add_value('price', price)
        image = hxs.select(u'//img[@id="prod-main-image"]/@src').extract()
        image = image[0] if image else ''
        loader.add_value('image_url', image)
        yield loader.load_item()
