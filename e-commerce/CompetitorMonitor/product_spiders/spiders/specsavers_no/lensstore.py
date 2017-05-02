# -*- coding: utf-8 -*-
"""
Customer: Specsavers NO
Website: https://www.yourlenses.no
Extract price from here http://screencast.com/t/NSeGUyLQsX
"""

import re
import json
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from product_spiders.spiders.specsavers_nz.specsaversitems import SpecSaversMeta


class LensStore(BaseSpider):
    name = "specsavers_no-lensstore.no"
    allowed_domains = ["lensstore.no"]
    start_urls = ['http://www.lensstore.no/linser']

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//div[@id="leftColumn"]//a/@href').extract()	
        for category in categories:
            yield Request(response.urljoin(category))

        promotion = response.xpath('//div[@id="articleListHead"]//div[span[contains(text(), "rabatt")]]//text()').extract()
        if promotion:
            promotion = [s for s in map(lambda x: x.strip(), promotion) if s != '']
            promotion = ' '.join(promotion)
        else:
            promotion = ''
        
        products = response.xpath('//div[contains(@class, "article_normal")]//h2/a/@href').extract()
        products += response.xpath('//li[@class="manufacturer"]//li/a/@href').extract()
        for product in products:
            yield Request(urljoin(base_url, product), callback=self.parse_product, meta={'promotion': promotion})

    def parse_product(self, response):
        base_url = get_base_url(response)

        identifier = response.xpath('//input[@name="product"]/@value').extract()
        if not identifier:
            replacement = response.xpath('//a[@class="btnAddCart2"]/@href').extract()
            yield Request(response.urljoin(replacement[0]), callback=self.parse_product)
            return

        name = response.xpath('//h1[@id="ArticleName"]//span/text()').extract()
        name = ' '.join(name)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        price = response.xpath('//div[@id="ArticlePrice"]/text()').re('\d+')
        loader.add_xpath('price', price[0])
        image_url = response.xpath('//a[@id="articleImage"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        loader.add_xpath('brand', '//tr[td[contains(text(), "Produsent")]]/td[contains(@class, "value")]/text()')
        loader.add_value('category', 'Kontaktlinser')
        loader.add_value('url', response.url)

        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        metadata = SpecSaversMeta()

        metadata['promotion'] = response.meta.get('promotion', '')

        item = loader.load_item()
        item['metadata'] = metadata
        yield item

