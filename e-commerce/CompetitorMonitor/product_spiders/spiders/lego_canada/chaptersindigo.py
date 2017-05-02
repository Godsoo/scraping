# -*- coding: utf-8 -*-

import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.utils import extract_price, fix_spaces

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class ChaptersIndigoSpider(BaseSpider):
    name = "legocanada-chapters.indigo.ca"
    allowed_domains = ["chapters.indigo.ca"]
    start_urls = ["https://www.chapters.indigo.ca/api/v1/search?facetIds=&searchKeys=Brand_en&searchTerms=lego&section=0&pageNumber=0&sortKey=&sortDirection=&categoryIds="]

    _re_sku = re.compile('(\d\d\d\d\d?)')

    def parse(self, response):
        base_url = get_base_url(response)
        
        data = json.loads(response.body)

        products = data['Products']
        for product in products:
            yield Request(response.urljoin(product['ProductUrl']), callback=self.parse_product)

        if products:
            next_page = data['Page'] + 1
            if next_page:
                next_url = add_or_replace_parameter(response.url, 'pageNumber', str(next_page))
                yield Request(next_url)


    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(selector=hxs, item=Product())

        name = response.xpath('//h1[@class="item-page__main-title"]/text()').extract()[0].strip()
        name = fix_spaces(name)
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        price = response.xpath('//div[@class="item-page__price--adjusted"]//span[@class="price"]/text()').extract()
        if not price:
            price = response.xpath('//p[@class="search-page__price--normal"]/text()').extract()

        price = extract_price(price[0]) if price else '0'
        loader.add_value('price', price)

        img_url = response.xpath('//img[contains(@class, "productPreview-image")]/@src').extract()
        if img_url:
            loader.add_value('image_url', urljoin(base_url, img_url[0]))

        loader.add_value('category', 'Lego')
        loader.add_value('brand', 'Lego')

        identifier = response.xpath('//meta[@property="og:upc"]/@content').extract()
        if not identifier:
            log.msg('ERROR >>> Product without identifier: ' + response.url)
            return

        loader.add_value('identifier', identifier[0])

        sku = self._re_sku.findall(name)
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)

        in_stock = response.xpath('//button[contains(@class, "Button __Button--primary") and contains(text(), "add to cart")]')
        if not in_stock:
            loader.add_value('stock', 0)

        yield loader.load_item()
