# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from urlparse import urljoin as urljoin_rfc


class GplshopSeSpider(BaseSpider):
    name = u'husqvarna_sweden-gplshop.se'
    allowed_domains = ['gplshop.se']
    start_urls = [
        'http://www.gplshop.se/'
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[@class="object_vertical object_menu"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # subcategories
        for url in hxs.select('//div[@class="shopwindow_articlegroup_grid shopwindow gridType5"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)
        category = hxs.select('//div[@class="breadcrumb"]//a/text()').extract()[1:]
        category = category[-3:]
        category.append(hxs.select('//div[@class="breadcrumb"]//b/text()').extract()[-1])
        # products
        for product in hxs.select('//div[@class="gridRowWrapper gridRowWrapper-prices-buttons"]//td[contains(@class,"gridItemContainer")]'):
            product_loader = ProductLoader(item=Product(), selector=product)
            image_url = product.select('.//img[@class="gridArticleImage"]/@src').extract()
            product_identifier = product.select('.//a[@class="buy"]/@href').re('(\d+)')
            if not product_identifier:
                continue
            product_name = product.select('.//a[@class="gridArticleName"]/text()').extract()[0].strip()
            product_loader.add_value('identifier', product_identifier[0])
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = product.select('.//span[@class="gridArticlePrice"]/text()').extract()
            if not price:
                price = product.select('.//span[@class="reducedPrice"]/text()').extract()
            price = extract_price(price[0].replace(':-', '').replace(' ', ''))
            sku = product.select('.//a[@class="gridArticleNr"]/text()').extract()
            sku = sku[0] if sku else ''
            product_loader.add_value('sku', sku)
            product_loader.add_value('price', price)
            url = product.select('.//a[@class="gridArticleName"]/@href').extract()[0]
            product_loader.add_value('url', urljoin_rfc(base_url, url))
            product_loader.add_value('category', category)
            product = product_loader.load_item()
            yield product