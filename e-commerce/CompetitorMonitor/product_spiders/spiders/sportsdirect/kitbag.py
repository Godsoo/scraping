# -*- coding: utf-8 -*-

import re
from copy import deepcopy
from time import time
from scrapy import Spider
from scrapy.http import Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from sportsdirectitems import SportsDirectMeta


class KitBagSpider(Spider):
    name = u'sportsdirect-kitbag.com'
    allowed_domains = ['kitbag.com']
    start_urls = ['http://www.kitbag.com/stores/kitbag/en/c/football/football-boots']

    cookies = {'KB_44_PriceZoneID': '3',
               'Kitbag_T36_NoFreeDelivery': 'False',
               'KB_44_Currency': 'GBP',
               'KB_44_CurrencyId': '1',
               'KB_44_LocationID': '204',
               'KB_44_LocationISO2': 'GB',
               'KB_44_Language': '1',
               'KB_44_network': 'KITBAG',
               'KB_44_BasketID': int(time()*1.305)}

    def parse(self, response):
        categories = response.xpath('//div[contains(@class, "facetCategory")]/div/a')
        for cat in categories:
            url = cat.select('@href').extract()[0]
            brand = cat.select('text()').re('(.*) Football Boots')[0]
            yield Request(response.urljoin(url), dont_filter=True, callback=self.parse_all_products, meta={'brand': brand})
            yield Request(response.urljoin(url), dont_filter=True, callback=self.parse_products, meta={'brand': brand})

    def parse_all_products(self, response):
        formdata = {}
        formdata['__VIEWSTATEGENERATOR'] = response.xpath('//input[@name="__VIEWSTATEGENERATOR"]/@value').extract()[0]
        formdata['__EVENTVALIDATION'] = response.xpath('//input[@name="__EVENTVALIDATION"]/@value').extract()[0]
        formdata['__EVENTTARGET'] = 'ctl00$ContentMain$browse$lv_pagingTop$lb_viewAll'
        formdata['ctl00$ScriptManager1'] = 'ctl00$ContentMain$browse$up_Product_Browse|ctl00$ContentMain$browse$lv_pagingTop$lb_viewAll'

        req = FormRequest.from_response(response,
                                        formname='aspnetForm',
                                        formdata=formdata,
                                        dont_filter=True,
                                        callback=self.parse_products,
                                        meta=response.meta)

        req.headers['User-Agent'] = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0'
        req.headers['X-MicrosoftAjax'] = 'Delta=true'
        req.headers['X-Requested-With'] = 'XMLHttpRequest'

        yield req

    def parse_products(self, response):
        products = response.xpath('//div[@class="productListItem"]/div[@class="productListLink"]/a/@href').extract()
        for url in products:
            meta = response.meta
            meta['dont_merge_cookies'] = True
            req = Request(response.urljoin(url),
                          cookies=self.cookies,
                          callback=self.parse_product,
                          meta=meta)
            yield req

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract_first() or response.xpath('//div[@id="pdTitle"]/h1/text()').extract_first()
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        image_url = ''.join(response.xpath('//img[@class="productImageRichSnippet"]/@src').extract()).split('?')[0]
        if image_url:
            loader.add_value('image_url', 'http:' + image_url)
        category = response.xpath('//span[@itemprop="title"]/text()').extract()
        loader.add_value('category', category[3:])
        price = response.xpath('//span[@itemprop="price"]/text()').extract_first() or response.xpath('//span[contains(@id, "PdProductPrice")]/text()').extract_first()
        price = extract_price(price) if price else ''
        loader.add_value('price', price)
        identifier = response.xpath('//span[@class="pdPid"]/text()').re('\d+')[0]
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('brand', response.meta['brand'])
        if price < 60:
            loader.add_value('shipping_cost', 4.50)
        else:
            loader.add_value('shipping_cost', 0)

        old_price = response.xpath('//div[@class="price"]/span[@class="pdPreviousPrice"]/del/text()').extract()
        old_price = old_price[0] if old_price else ''

        item = loader.load_item()

        size_options = response.xpath('//select[@class="pdSizes"]/option[@value!="0"]')
        if size_options:
            for size_option in size_options:
                option = deepcopy(item)
                size, tmp , status = ''.join(size_option.select('text()').extract()).partition(' - ')

                option['identifier'] += '-' + size_option.select('@value').extract()[0]
                option['name'] += ' ' + ''.join(re.findall('\d+', size))

                if 'out of stock' in status.lower() or 'pre order' in status.lower() or 'pre-order' in status.lower() or not option['price']:
                    option['stock'] = 0

                metadata = SportsDirectMeta()
                metadata['size'] = size
                metadata['rrp'] = old_price
                option['metadata'] = metadata
                yield option
        else:
            if not item['price']:
                item['stock'] = 0

            size = response.css('.pdSingleSize').xpath('text()').re('\S+')
            if size:
                metadata = SportsDirectMeta()
                metadata['size'] = size[0]
                metadata['rrp'] = old_price
                item['metadata'] = metadata
            yield item
