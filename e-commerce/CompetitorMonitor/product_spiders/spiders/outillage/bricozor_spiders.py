# -*- coding: utf-8 -*-

import re
import os
import json
from urllib import urlencode
from itertools import cycle, product as iter_product

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url

from product_spiders.middlewares import PROXIES
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price_eu

HERE = os.path.abspath(os.path.dirname(__file__))


class BricozorSpider(BaseSpider):
    name = 'bricozor.com'
    allowed_domains = ['bricozor.com']

    start_urls = ['http://www.bricozor.com/sitemap.xml']

    handle_httpstatus_list = [403]
    errors = []
    _proxies = cycle(PROXIES)

    _user_agent_list = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:26.0) Gecko/20100101 Firefox/26.0',
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:26.0) Gecko/20100101 Firefox/26.0',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:26.0) Gecko/20100101 Firefox/26.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:25.0) Gecko/20100101 Firefox/25.0'
    ]

    #website_id = 1000044

    #new_system = True
    #old_system = True
    deduplicate_identifiers = True

    def parse(self, response):
        urls = re.findall(r'<loc>(.*)</loc>', response.body)
        for url in urls:
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        if response.status == 403:
            retry = response.meta.get('retry', 0)
            if retry < 500:
                meta = response.meta.copy()
                meta['retry'] = retry + 1
                self.log('>>> Retrying No. %s => %s' % (meta['retry'], response.url))
                yield Request(response.url,
                              dont_filter=True,
                              meta=meta,
                              callback=self.parse_product)
            return
        name = " ".join(hxs.select('//div[@id="product-page-header-wrapper"]/h1//span/text()').extract()).strip()
        brand = hxs.select('//div[@id="product-page-header-wrapper"]/h1/a/span/text()').extract()
        identifier = hxs.select('//article[@id="product-page-container"]/@data-id').extract()[0]
        image_url = hxs.select('//img[@itemprop="thumbnail"]/@src').extract()
        if not image_url:
            image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        category = [" ".join([y.strip() for y in(x.strip().split())]) for x in hxs.select('//ol[@class="breadcrumb"]/li/a/span[@itemprop="title"]/text()').extract()]

        options = hxs.select('//form[@id="article-selector"]/ul/li/ul/li/input')
        opts = {}
        if options:
            for option in options:
                value = option.select('@value').extract()[0]
                ids = json.loads(option.select('@data-articles-ids').extract()[0])
                for id in ids:
                    if id in opts:
                        opts[id].append(value)
                    else:
                        opts[id] = [value]
            for opt_id, opt_values in opts.items():
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', "%s %s" % (name, " ".join(opt_values)))
                loader.add_value('identifier', "%s_%s" % (identifier, opt_id))
                loader.add_value('url', response.url)
                loader.add_value('stock', 1)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                if brand:
                    loader.add_value('brand', brand[0])
                if category:
                    loader.add_value('category', category)
                url = "http://www.bricozor.com/product/article-selector/?articles_ids=%s&product_id=%s" % (opt_id, identifier)
                yield Request(url, callback=self.parse_option, meta={'product': loader.load_item()})
        else:
            sku = hxs.select('//strong[@itemprop="sku"]/text()').extract()
            if not sku:
                sku = hxs.select('//p[@class="article-reference"]/strong/text()').extract()
            price = extract_price_eu(hxs.select('//span[@class="price" or @class="new-price"]/text()').extract()[0].replace(u'\xa0', ''))
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('identifier', identifier)
            loader.add_value('url', response.url)
            loader.add_value('stock', 1)
            if sku:
                loader.add_value('sku', sku[0])
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            if brand:
                loader.add_value('brand', brand[0])
            if category:
                loader.add_value('category', category)

            yield loader.load_item()

    def parse_option(self, response):

        if response.status == 403:
            retry = response.meta.get('retry', 0)
            if retry < 500:
                meta = response.meta.copy()
                meta['retry'] = retry + 1
                self.log('>>> Retrying No. %s => %s' % (meta['retry'], response.url))
                yield Request(response.url,
                              dont_filter=True,
                              meta=meta,
                              callback=self.parse_option)
            return
        data = json.loads(response.body)
        hxs_price = HtmlXPathSelector(text=data['product_price'])
        hxs_aside = HtmlXPathSelector(text=data['product_aside'])
        price = extract_price_eu(hxs_price.select('//span[@class="price" or @class="new-price"]/text()').extract()[0].replace(u'\xa0', ''))
        sku = hxs_aside.select('//strong[@itemprop="sku"]/text()').extract()
        if not sku:
            sku = hxs_aside.select('//p[@class="article-reference"]/strong/text()').extract()
        product = response.meta.get('product')
        product['price'] = price
        if sku:
            product['sku'] = sku[0]
        yield product
