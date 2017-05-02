# -*- coding: utf-8 -*-

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class SnailRuSpider(BaseSpider):
    name = "snail.ru"
    allowed_domains = ['snail.ru']
    start_urls = ['http://www.snail.ru']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//div[@id="left_submenu"]//a/@href').extract()
        category_urls += hxs.select('//ul[@class="menu"]//li/a/@href').extract()

        for url in category_urls:
            if 'ucenennye_tovary' not in url:
                yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        sub_categories = hxs.select('//div[contains(@class, "subgroup")]//h2/a/@href').extract()
        for url in sub_categories:
            yield Request(urljoin(base_url, url), callback=self.parse_category)

        product_urls = hxs.select('//div[@id="items"]//div[contains(@class, "block item")]//a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

        next_category_urls = hxs.select('//div[@id="pagination"][1]//li/a/@href').extract()[:-1]
        for url in next_category_urls:
            yield Request(urljoin(base_url,url), callback=self.parse_category)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_xpath('name', '//h1[@id="item_breadcrumbs_title"]/text()')
        loader.add_value('url', response.url)
        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//div[contains(@class, "item_data")]//div[@class="side_values"]/div[@class="price"]/span[@class="price"]/text()').extract()

        price = ''.join(price[0].split())
        price = float(price)
        loader.add_value("price", price)
        if price < 15000:
            shipment = 350
        else:
            shipment = 0
        loader.add_value('shipping_cost', shipment)
        image_url = hxs.select('//div[@class="img-wrapper"]/img/@data-cloudzoom').re('Image:"(.*)", ')
        if not image_url:
            image_url = hxs.select('//div[@class="item_image"]//img/@src').extract()
            if not image_url:
                image_url = hxs.select('//div[@id="cloud_img"]/img/@src').extract()
        image_url = image_url[0] if image_url else ''
 
        loader.add_value('image_url', image_url)
        loader.add_xpath('brand', '//div[@id="brand"]//span[@itemprop="name"]/text()')
        categs = hxs.select('//div[@id="breadcrumbs"]/ul//li/a/span[@itemprop="title"]/text()').extract()
        category = ' > '.join(categs[1:])
        loader.add_value('category', category)
        #stock_str = hxs.select('//div[@class="delivery_status"]/span/text()').extract()
        #if stock_str:
        #    stock_str = stock_str[0]
        #    if stock_str == u'в наличии':
        #        stock = 1
        #    elif stock_str == u'уточняйте':
        #        stock = 0
        #    else:
        #        stock = 0


        if price == 0:
            loader.add_value('stock', 0)
        identifier = hxs.select('//td[@class="value"][@itemprop="identifier"]/text()').extract()
        if not identifier:
            log.msg('Product without identifier: ' + response.url)
            return

        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)

        yield loader.load_item()
