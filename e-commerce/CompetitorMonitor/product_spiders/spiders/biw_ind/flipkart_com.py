# -*- coding: utf-8 -*-

import os
import csv
import paramiko
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter, url_query_cleaner

from product_spiders.spiders.biw_ind.biwind_feed import BIWINDSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class FlipkartSpider(BIWINDSpider):
    name = u'bi_worldwide_br-www.flipkart.com'
    allowed_domains = ['www.flipkart.com']
    start_urls = ('http://www.biworldwide.com', )
    handle_httpstatus_list = [500]

    def __init__(self, *args, **kwargs):
        super(FlipkartSpider, self).__init__(*args, **kwargs)

        self.brands = set()
        self.identifiers = []

    def parse(self, response):
        for product in super(FlipkartSpider, self).parse(response):
            self.brands.add(product['brand'])

        url = 'http://www.flipkart.com/all-categories/pr?p%5B%5D=sort%3Dprice_asc&sid=search.flipkart.com&start=1&ajax=true'
        for brand in self.brands:
            url = add_or_replace_parameter(url, 'q', brand)
            yield Request(url, callback=self.parse_products_list, meta={'dont_merge_cookies': True})

    def parse_products_list(self, response):
        if response.status == 500 and response.meta.get('retries', 0) < 10:
            meta = response.meta
            meta['retries'] = meta.get('retries', 0) + 1
            meta['dont_merge_cookies'] = True
            yield Request(response.url, meta=meta, dont_filter=True, callback=self.parse_products_list)
            return

        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        urls = hxs.select('//a[@data-tracking-id="prd_title"]/@href').extract()
        for url in urls:
            url = url_query_cleaner(url, ('pid',))
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'dont_merge_cookies': True})

        # pagination
        if len(urls) > 0:
            start = int(url_query_parameter(response.url, 'start')) + len(urls)
            url = add_or_replace_parameter(response.url, 'start', str(start))
            meta = response.meta
            meta['dont_merge_cookies'] = True
            yield Request(url, meta=meta, callback=self.parse_products_list)
        elif len(urls) < 20 and response.meta.get('retries', 0) < 10:
            meta = response.meta
            meta['dont_merge_cookies'] = True
            meta['retries'] = meta.get('retries', 0) + 1
            yield Request(response.url, meta=meta, dont_filter=True, callback=self.parse_products_list)

    def parse_product(self, response):
        if response.status == 500 and response.meta.get('retries', 0) < 3:
            meta = response.meta
            meta['retries'] = meta.get('retries', 0) + 1
            meta['dont_merge_cookies'] = True
            yield Request(response.url, meta=meta, dont_filter=True, callback=self.parse_product)
            return


        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        try:
            name = hxs.select('//div[@data-tracking-id="product_breadCrumbs"]//strong/text()').extract()[0].strip()
        except:
            retry = response.meta.get('retry', 0) + 1
            if retry < 10:
                yield Request(response.url, callback=self.parse_product, meta={'retry': retry}, dont_filter=True)
            else:
                self.log('Warning!!! Giving up retrying: {}'.format(response.url))
            return

        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        subtitle = hxs.select('//div[contains(@class, "title-wrap")]/span[@class="subtitle"]/text()').extract()
        if subtitle:
            name = name + ' ' + subtitle[0]

        options = hxs.select('//div[@class="multiSelectionWidget-selectors-wrap"]')
        sel_options = ''
        if options:
            # get selected
            sel_options = ' ' + ' '.join(hxs.select('//div[contains(@class,"multiSelectionWidget-selector") and contains(@class,"current")]//span/text()').extract())
            sel_options += ' '.join(options.select('.//select/option[@data-current="true"]/@value').extract())
            if len(options) > 2:
                self.log('MULTIPLE OPTIONS2 FOUND!!! {}'.format(response.url))
            urls = options.select('.//a/@href').extract()
            urls.extend(options.select('.//option/@data-url').extract())
            for option_url in urls:
                pid = url_query_parameter(option_url, 'pid')
                if pid not in self.identifiers:
                    url = url_query_cleaner(option_url, ('pid',))
                    yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        brand = hxs.select('//div[@class="title-wrap line fk-font-family-museo section omniture-field"]/@data-prop41').extract()
        brand = brand[0].strip() if brand else ''
        dealer = hxs.select('//a[@class="seller-name"]/text()').extract()
        dealer = dealer[0].strip() if dealer else ''

        identifier = url_query_parameter(response.url, 'pid')
        price = hxs.select('//meta[@itemprop="price"]/@content').extract()
        if price:
            price = extract_price(price[0])
        else:
            price = 0
        category = hxs.select('//div[@data-tracking-id="product_breadCrumbs"]//a/@data-tracking-id').extract()[1:4]
        image_url = hxs.select('//div[@class="imgWrapper"]/img/@data-src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        out_of_stock = hxs.select('//div[@class="out-of-stock-section"]')
        coming_soon = hxs.select('//div[@class="coming-soon-section"]')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('brand', brand)
        loader.add_value('name', name + sel_options)
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        loader.add_value('category', category)
        loader.add_value('image_url', image_url)
        loader.add_value('dealer', dealer)
        if out_of_stock or coming_soon:
            loader.add_value('stock', 0)

        product = loader.load_item()

        if product['identifier'] not in self.identifiers:
            self.identifiers.append(product['identifier'])
            yield product

