# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
from urlparse import urljoin as urljoin_rfc
import re
from decimal import Decimal

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class LegacikSkSpider(LegoMetadataBaseSpider):
    name = u'legacik.sk'
    allowed_domains = ['www.legacik.sk']
    start_urls = [
        u'http://www.legacik.sk',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # categories
        urls = hxs.select('//*[@id="inleft_eshop"]//a/@href').extract()
        for url in urls:
            if url != '/legacik/eshop/4-1-LEGO-SERVICE-suciastky':
                yield Request(urljoin_rfc(base_url, url), callback=self.parse)
        # pagination
        urls = hxs.select('//div[@class="pagination"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)
        # products
        # urls = hxs.select('//div[@class="productTitleContent"]/a/@href').extract()
        # for url in urls:
        #     yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        products = hxs.select('//div[@class="productBody"]')
        category = hxs.select('//*[@id="wherei"]/p//a/text()').extract()
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = product.select('.//div[@class="productTitleContent"]/a/text()').extract()[0].strip()
            url = product.select('.//div[@class="productTitleContent"]/a/@href').extract()[0]
            loader.add_value('url', urljoin_rfc(base_url, url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', './/div[@class="img_box"]/a/img[1]/@src',
                             Compose(lambda v: urljoin(base_url, v[0])))
            price = product.select('.//*[@itemprop="price"]/text()').extract()
            try:
                price = extract_price_eu(price[0].strip())
            except:
                price = Decimal('0.0')
            loader.add_value('price', price)
            if category:
                loader.add_value('category', category[-1])
            results = re.search(r"\b([\d]+)\b", name)
            if results:
                loader.add_value('sku', results.group(1))
            identifier = product.select('.//div[@class="img_box"]/a/img[1]/@rel').extract()[0]
            loader.add_value('identifier', identifier)
            availability = product.select('.//div[@class="stock_no"]').extract()
            if availability or not price:
                loader.add_value('stock', 0)
            loader.add_value('brand', 'LEGO')
            if price <= 15:
                loader.add_value('shipping_cost', 2.80)
            elif price <= 29:
                loader.add_value('shipping_cost', 4.5)
            elif price <= 149:
                loader.add_value('shipping_cost', 4.99)
            else:
                loader.add_value('shipping_cost', 0)
            yield self.load_item_with_metadata(loader.load_item())
