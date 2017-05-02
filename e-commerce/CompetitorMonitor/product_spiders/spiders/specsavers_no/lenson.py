# -*- coding: utf-8 -*-
"""
Customer: Specsavers NO
Website: https://www.lenson.com
Products to monitor: Only extract products from this category on site http://screencast.com/t/0KPo6N5GtYWX

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4723-specsavers-no-|-lenson-com-|-new-spider/details#

"""

import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from urlparse import urljoin

from product_spiders.spiders.specsavers_nz.specsaversitems import SpecSaversMeta

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader



class Lenson(BaseSpider):
    name = "specsavers_no-lenson.com"
    allowed_domains = ["lenson.com"]
    start_urls = ['https://www.lenson.com/no/api/filter/?top_category_id=1&hub_id=29&categories_id=29&language=no&sort=popularity&p=0&cache=true&dataType=html']

    def parse(self, response):
        base_url = get_base_url(response)

        products = json.loads(response.body)['products']
        for product in products:
            yield Request(urljoin(base_url, product['link']), callback=self.parse_product)

        if products:
            page = int(url_query_parameter(response.url, 'p', '0'))
            page += 1
            yield Request(add_or_replace_parameter(response.url, 'p', str(page)))

    def parse_product(self, response):
        base_url = get_base_url(response)

        name = response.xpath('//h1[@class="product-view__title"]/span/text()').extract()
        name = map(lambda x: x.strip(), name)
        name = ' '.join(name)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_xpath('price', '//div[contains(@class, "product-view__total-price")]/@data-price')
        image_url = response.xpath('//img[@itemprop="image"]/@alt').extract()
        if image_url:
            loader.add_value('image_url', 'http:' + image_url[0])
        loader.add_xpath('brand', '//div[@class="product-view__brand brand"]/img[@class="brand__image"]/@alt')
        loader.add_value('category', 'Kontaktlinser')
        loader.add_value('url', response.url)
        identifier = re.findall('"ecomm_prodid":"(\d+)","', response.body)[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)

        metadata = SpecSaversMeta()
        promotion = response.xpath('//section[contains(@class, "product-view--product-page")]//figcaption[@class="splash__inner"]//text()').extract()
        if promotion:
            promotion = [s for s in map(lambda x: x.strip(), promotion) if s != '']
            promotion = ' '.join(promotion)
        else:
            promotion = ''
        metadata['promotion'] = promotion

        item = loader.load_item()
        item['metadata'] = metadata
        yield item
