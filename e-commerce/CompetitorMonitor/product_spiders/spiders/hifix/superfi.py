import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

import csv

from product_spiders.items import Product, ProductLoader


class SuperFiSpider(BaseSpider):
    name = 'superfi.co.uk'
    allowed_domains = ['www.superfi.co.uk', 'superfi.co.uk']
    start_urls = ('http://www.superfi.co.uk/',)

    def __init__(self, *args, **kwargs):
        super(SuperFiSpider, self).__init__(*args, **kwargs)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select(u'//ul[@class="topnav"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        # pages
        next_page = hxs.select(u'//div[@class="paging2"]//a[contains(text(),">>")]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url)

        # products
        products = hxs.select(u'//a[@class="compare_list_image"]/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

    def parse_option_price(self, response):
        product_loader = ProductLoader(item=Product(), response=response)

        product_loader.add_value('name', response.meta['name'])
        product_loader.add_value('url', response.meta['url'])
        product_loader.add_xpath('price', u'//div[@class="webPriceLabel"]/text()', re=r'([\d.,]+)')
        product_loader.add_xpath('identifier', '//p/text()', re=r'Product code: (\w+)')

        product_item = product_loader.load_item()
        if product_item.get('identifier'):
            yield product_item

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        base_name = hxs.select(u'//div[@class="ProductTopTitle"]/h1/text()').extract()
        multiple_options = hxs.select('//div[@class="variantdiv"]')
        if not multiple_options:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', base_name)
            product_loader.add_value('url', response.url)
            product_loader.add_xpath('price', u'//div[@class="webPriceLabel"]/text()', re=r'([\d.,]+)')
            product_loader.add_xpath('identifier', '//p/text()', re=r'Product code: (\w+)')
            product_item = product_loader.load_item()
            if product_item.get('identifier'):
                yield product_item
        else:
            options_url = 'http://www.superfi.co.uk/Handlers/productcolorsizeinfo.ashx'
            color_options = multiple_options.select(u'.//select[contains(@id,"Color")]/option/@value').extract()
            size_options = multiple_options.select(u'.//select[contains(@id,"Size")]/option/@value').extract()

            product_id = hxs.select('//input[contains(@name, "ProductID")]/@value').extract()[0]
            variant_id = hxs.select('//input[contains(@name, "VariantID")]/@value').extract()[0]
            data_string = ('productid=' + str(product_id) +
                           '&vid=' + str(variant_id) +
                           '&color=%(color)s&size=%(size)s&CustomerLevelID=0&AffiliateID=0&varainHId=0')
            headers = {'Content-type': 'application/x-www-form-urlencoded',
                       'X-Requested-With': 'XMLHttpRequest',
                       'Connection': 'keep-alive',
                       'Pragma': 'no-cache',
                       'Cache-Control': 'no-cache'}
            if color_options:
                for color in color_options[1:]:
                    if size_options:
                        for size in size_options[1:]:
                            params = {'color': color,
                                      'size': size}
                            h = headers.copy()
                            h['Content-Length'] = str(len(data_string % params))
                            yield Request(options_url,
                                          body=data_string % params,
                                          method='POST',
                                          dont_filter=True,
                                          headers=h,
                                          callback=self.parse_option_price,
                                          meta={'name': base_name[0] + ' ' + size + ' ' + color,
                                                'url': response.url})
                    else:
                        params = {'color': color,
                                  'size': ''}
                        h = headers.copy()
                        h['Content-Length'] = str(len(data_string % params))
                        yield Request(options_url,
                                      body=data_string % params,
                                      method='POST',
                                      dont_filter=True,
                                      headers=h,
                                      callback=self.parse_option_price,
                                      meta={'name': base_name[0] + ' ' + color,
                                            'url': response.url})
            elif size_options:
                for size in size_options[1:]:
                    params = {'color': '',
                              'size': size}
                    h = headers.copy()
                    h['Content-Length'] = str(len(data_string % params))
                    yield Request(options_url,
                                  body=data_string % params,
                                  method='POST',
                                  dont_filter=True,
                                  headers=h,
                                  callback=self.parse_option_price,
                                  meta={'name': base_name[0] + ' ' + size,
                                        'url': response.url})
