# -*- coding: utf-8 -*-
"""
Customer: Specsavers NL
Website: https://www.lenson.nl
Products to monitor: Only extract products from this category on site http://screencast.com/t/0KPo6N5GtYWX

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4757

"""

import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader



class Lenson(BaseSpider):
    name = "specsavers_nl-lenson.nl"
    allowed_domains = ["lenson.nl"]
    start_urls = ['https://www.lenson.nl/api/filter/?top_category_id=1&hub_id=29&categories_id=29&language=nl&p=0']

    def parse(self, response):
        base_url = get_base_url(response)

        data = json.loads(response.body)
        products = data['products']
        
        if products:
            page = int(data['p'])
            page += 1
            yield Request(add_or_replace_parameter(response.url, 'p', str(page)))
        else:
            return

        for product in products:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', product['products_id'])
            loader.add_value('sku', product['products_id'])
            loader.add_value('name', product['products_name'])
            loader.add_value('name', product.get('products_model'))
            loader.add_value('price', product['products_price_float'])
            loader.add_value('url', response.urljoin(product['link']))
            loader.add_value('brand', product['manufacturers_name'])
            loader.add_value('image_url', response.urljoin(product['products_image']))
            yield loader.load_item()


    def parse_product(self, response):
        base_url = get_base_url(response)

        name = response.xpath('//div[@class="lensname"]/h1/text()').extract()[0].strip()
        model_name = response.xpath('//div[@class="lensname"]/span[@class="name-model"]/text()').extract()
        if model_name:
            name = name + ' ' + model_name[0]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        price = response.xpath('//div[@id="tiered_box_red"]//tr[td[text()="1"]]/td/strong/text()').extract()
        if not price:
            price = response.xpath('//meta[@itemprop="price"]/@content').extract()[0]
        loader.add_value('price', price)
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        categories = response.xpath('//div[@id="prodBreadCrumbs"]/a/text()').extract()
        loader.add_value('category', categories)
        loader.add_value('url', response.url)
        identifier = re.findall('productsId = "(\d+)";', response.body)[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        yield loader.load_item()
