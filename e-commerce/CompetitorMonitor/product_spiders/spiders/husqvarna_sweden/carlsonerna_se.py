# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
from copy import deepcopy
from scrapy import log
import re


class CarlsonernaSpider(BaseSpider):
    name = u'carlsonerna.se'
    allowed_domains = ['www.carlsonerna.se']
    start_urls = [
        u'http://www.carlsonerna.se/',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@id="content_categories"]//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)


    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcategories = hxs.select('//div[contains(@class, "category_slot")]/table/tr/td/a/@href').extract()

        for category in subcategories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)

        products = hxs.select('//div[contains(@class, "product_slot")]/table/tr/td[1]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next_pages = hxs.select('//div[contains(@class, "right") and contains(text(), "Sida")]/a/@href').extract()
        for page in next_pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse_category)


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//ul/li[contains(@class, "cl_unfolded")]/a/text()').extract()
        name = hxs.select('//h1/text()').extract() or hxs.select('//span[@id="extra-info"]/text()').extract()
        image_url = hxs.select('//a[@id="main-product-image"]/img/@src').extract()
        price = hxs.select('//span[@class="product_price"]/text()').extract()
        sku = hxs.select('//span[@class="art_no"]/text()').extract() or [""]
        identifier = hxs.select('//form[@class="product_form"]/input[@class="product_id"]/@value').extract()[0].strip()

        if not price:
            return

        price = extract_price_eu(price[0])
        loader = ProductLoader(item=response.meta.get('product', Product()), selector=hxs)
        loader.add_value('url', response.url)
        loader.add_value('name', name[0].strip())
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        for category in categories:
            loader.add_value('category', category)
        loader.add_value('price', price)
        loader.add_value('sku', sku[0])
        loader.add_value('identifier', identifier)
        yield Request('http://www.carlsonerna.se/js/product/%s' % identifier, callback=self.parse_options, meta={'product': loader.load_item()})


    def parse_options(self, response):

        product = response.meta.get('product', Product())
        subid = re.findall('sub_product.product_id = ([0-9]+);', response.body)
        subname = re.findall('sub_product.product_name = "(.*)";', response.body)
        subprice = re.findall('sub_product.price = "(.*)";', response.body)

        if subid and subname:
            for id, name, price in zip(subid, subname, subprice):
                option = deepcopy(product)
                loader = ProductLoader(item=option, selector="")
                loader.replace_value('name', name.decode("unicode_escape"))
                loader.replace_value('identifier', "%s-%s" % (option['identifier'], id))
                price = price.decode("unicode_escape").replace(":", "").replace("-", "")
                stock = 1 if price and not price == '0' else 0
                loader.replace_value('price', price)
                loader.add_value('stock', stock)
                yield loader.load_item()

        else:
            loader = ProductLoader(item=product, selector="")
            stock = 1 if loader.get_value('price') else 0
            loader.replace_value('stock', stock)
            yield loader.load_item()
