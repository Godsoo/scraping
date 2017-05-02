# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc
import json
import re


class SwooneditionsComSpider(BaseSpider):
    name = u'made-swooneditions.com'
    allowed_domains = ['swooneditions.com']
    start_urls = [
        'https://www.swooneditions.com'
    ]
    

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        self.products = set()
        # categories
        categories = hxs.select('//ul[@class="nav nav--inline"]//a')
        for category in categories:
            cat_name = category.select('./text()').extract()
            if not cat_name:
                continue
            cat_name = cat_name[0].strip()
            if not cat_name:
                continue
            url = category.select('./@href').extract()[0]
            yield Request(urljoin_rfc(base_url, url + '?p=0&ajax_request=1'),
                          callback=self.parse_categories,
                          meta={'category': cat_name})

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = response.meta['category']
        # products
        for url in hxs.select('//div[@class="grid__cell desk-6-2 lap-6-3"]/a/@href').extract():
            if url.endswith('/'):
                url = url[:-1]
            if url.split('/')[-1] not in self.products:
                self.products.add(url.split('/')[-1])
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})
        # pages
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories, meta={'category': category})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = response.meta['category']
        image_url = hxs.select('//img[@class="zoom-image"]/@src').extract()
        match = re.search(r"window\.universal_variable\.product = (\{.*?\});",
                          response.body, re.DOTALL | re.IGNORECASE | re.MULTILINE)
        if match:
            result = match.group(1)
            data = json.loads(result)
            product_identifier = data['id']
            sku = data['sku_code']
            product_name = data['name']
            price = hxs.select('//*[@id="product-price-{}"]/span/text()'.format(product_identifier)).extract()[0]
            price = extract_price(price)
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('category', category)
            product_loader.add_value('sku', sku)
            product_loader.add_value('shipping_cost', 0)
            yield product_loader.load_item()
        else:
            self.log("ERROR: no json {}".format(response.url))
