# -*- coding: utf-8 -*-

import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.utils import extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log


class HazelsBoulderSpider(BaseSpider):
    name = 'applejack-hazelsboulder.com'
    allowed_domains = ['hazelsboulder.com', 'hazelsworld.com']
    start_urls = ('http://www.hazelsboulder.com/',)
    categories = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//div[@id="layTopMenu"]//a')
        for category in categories:
            url = category.select('@href').extract()[0]
            category_name = category.select('text()').extract()[0]
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta={'category': category_name})

        categories = hxs.select('//td[contains(text(), "Select your category")]//div/a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta)

        if not response.meta.get('ignore_categories', False) and '_select=' not in response.url:
            categories_selector = hxs.select('//select[contains(@id, "_select")]')
            for category_selector in categories_selector:
                category = category_selector.select('@name').extract()[0]
                for category_value in category_selector.select('option/@value').extract():
                    if category_value not in self.categories:
                        self.categories.append(category_value)
                        values = category_value.split('_')
                        if len(values)>1:
                            url = add_or_replace_parameter(response.url, category, values[-1])
                            url = add_or_replace_parameter(url, 'sel_category', values[-1])
                            url = add_or_replace_parameter(url, 'type', values[0])
                        else:
                            url = add_or_replace_parameter(response.url, category, category_value)
                            url = add_or_replace_parameter(url, 'sel_category', category_value)
                        meta = meta=response.meta
                        meta['ignore_categories'] = True
                        yield Request(url, meta=meta)

        # products
        products = response.xpath('//a[@class="Srch-producttitle"]/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

        # pagination
        next_page = hxs.select('//a[b[contains(text(), ">>")]]/@href').re('\d+')
        if next_page:
            next_page = add_or_replace_parameter(response.url, 'pagereq', next_page[0])
            yield Request(next_page, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('url', response.url)
        name = ' '.join(hxs.select('//span[@class="producttitle"]/text()').extract()[0].split())

        price = response.css('span.SalePrice::text').extract_first() or response.css('span.RegularPrice::text').extract or 0

        loader.add_value('name', name)
        loader.add_value('price', price)

        categories = hxs.select('//span[contains(text(), "Type")]/following-sibling::span[@class="iteminfo"]//text()').extract()
        loader.add_value('category', response.meta['category'])

        loader.add_value('brand', '')

        image_url = response.xpath('//div[@id="loadarea"]/img/@src').extract()
        if image_url:
            image_url = image_url[-1]
            if 'not_available' in image_url:
                loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url))
            else:
                loader.add_value('image_url', 'http:' + image_url)

        identifier = hxs.select('//div[@id="bmg_itemdetail_sku"]/text()').re('\d+')
        loader.add_value('identifier', identifier[0])
        loader.add_value('sku', identifier[0])
        yield loader.load_item()
