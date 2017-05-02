# -*- coding: utf-8 -*-
import os
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class BlivakkerSpider(BaseSpider):
    name = 'blivakker.no'
    allowed_domains = ['blivakker.no']
    start_urls = ['http://www.blivakker.no']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//*[@id="mainNav"]/div[@class="mainNavElement"]/a[@href!="/"]/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url, callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        hxs = HtmlXPathSelector(response)
        sub_categories = hxs.select('//*[@id="contentWrapper"]/div/div[@class="categoryElement"]/a/@href').extract()
        for sub_category in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_category)
            yield Request(url, callback=self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//*[@id="contentWrapper"]/div/div[@class="productElement"]')
        if products:
            category = hxs.select('//div[@class="contentHeader"]/h1/span/text()').extract()[0]
            brands = hxs.select('//div[@class="midCategory"]/select/option/text()').extract()[2:]
            for product in products:
                loader = ProductLoader(item=Product(), selector=product)
                sku = ''.join(product.select('h2/a/@href').extract()).split('/')[-2]
                loader.add_value('sku', sku)
                loader.add_value('identifier', sku)
                loader.add_xpath('name', 'h2/a/text()')
                url = urljoin_rfc(get_base_url(response), ''.join(product.select('h2/a/@href').extract()))
                loader.add_value('url', url)
                price = ''.join(product.select('div[@class="productElementPrice"]/text()').extract()).strip().replace(u'\xa0', '')
                loader.add_value('price', price.replace(',', '.'))
                loader.add_xpath('image_url', 'div[@class="productElementImg"]//img/@src')
                loader.add_value('category', category)
                loader.add_value('brand', match_brand(loader.get_output_value('name'), brands))

                yield loader.load_item()
            next_page = hxs.select('//a[@class="nextprevSC" and text()=" Neste side"]/@href').extract()
            if next_page:
                url = urljoin_rfc(get_base_url(response), next_page[0])
                yield Request(url, callback=self.parse_products)
        sub_categories = hxs.select('//*[@id="contentWrapper"]/div/div[@class="categoryElement"]/a/@href').extract()
        if sub_categories:
            yield Request(response.url, callback=self.parse_subcategories, dont_filter=True)

def match_brand(product_name, brands):
    for brand in brands:
        if brand.lower() in product_name.lower():
            return brand

    for brand in brands:
        if brand_fuzzy_match(product_name, brand):
            return brand
    matches = [
        (u'Rock Cosmetics', u'Rock Beauty'),
        (u'Sexy Hair', u'Sex Symbol'),
    ]
    for match1, match2 in matches:
        if match2.lower() in product_name.lower() or match1.lower() in product_name.lower():
            return match1
    return None

def brand_fuzzy_match(product_name, brand):
    from product_spiders.fuzzywuzzy.fuzz import ratio, partial_ratio
    from product_spiders.fuzzywuzzy import utils

    s1 = utils.full_process(product_name)
    s2 = utils.full_process(brand)

    if ratio(s1, s2) > 80:
        return True
    if partial_ratio(s1, s2) > 80:
        return True
    return False