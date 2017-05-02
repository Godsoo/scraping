# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4552
"""
import re
import json
from urlparse import urljoin

from scrapy import Spider, Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.utils.url import url_query_parameter

from product_spiders.items import ProductLoaderWithNameStrip as ProductLoader, Product


class LensonSpider(Spider):
    name = 'specsavers_ie-lenson.com'
    allowed_domains = ('lenson.com', )
    search_url = 'https://www.lenson.com/ie/category_ajax.php?p={}&sort=products_name_asc&categories_id=29'
    start_urls = [search_url.format(0)]

    def parse(self, response):
        result = json.loads(response.body)
        page = url_query_parameter(response.url, 'p')
        hxs = HtmlXPathSelector(text=result['html'])
        product_urls = hxs.select('//li/a/@href').extract()
        self.log('{} products found'.format(len(product_urls)))
        for url in product_urls:
            yield Request(url, callback=self.parse_product)

        if result['is_there_a_next_page']:
            yield Request(self.search_url.format(int(page) + 1))

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', response.url.split('-')[-1].split('.')[0])
        loader.add_xpath('name', '//meta[@itemprop="name"]/@content')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        categories = response.xpath('//div[@id="prodBreadCrumbs"]//a/text()').extract()
        for cat in categories:
            loader.add_value('category', cat)
        if loader.get_output_value('price') is None:
            delisted_text = response.xpath('//span[@class="markup-blu markup-lg"]/text()')
            if delisted_text and 'discontinued' in delisted_text.extract()[0].lower():
                self.log('delisted product {}'.format(response.url))
                return
            loader.add_value('stock', 0)
            loader.add_value('price', 0)
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        loader.add_value('url', response.url)
        yield loader.load_item()
