import re
import os
import csv
import cStringIO

import time

from decimal import Decimal
from utils import extract_price_eu

from scrapy import log
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url


from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

from product_spiders.base_spiders import BaseAmazonSpider

def append_request(url, callback, meta):
    meta['requests'].append(Request(url, callback=callback, meta=meta, dont_filter=True))

def append_request_suggested(url, callback, meta):
    meta = dict(meta)
    meta['suggested_search_peek'] = True
    meta['requests'].append(Request(url, callback=callback, meta=meta, dont_filter=True))


class AmazonSpider(BaseAmazonSpider):
    name = 'bricoman-amazon.it-base'
    all_sellers = False
    #_use_amazon_identifier = True
    #exclude_sellers = ['Amazon']

    #download_delay = 1.0
    #randomize_download_delay = True

    def __init__(self, *args, **kwargs):
        super(AmazonSpider, self).__init__('www.amazon.it', *args, **kwargs)

    def start_requests(self):
        with open(os.path.join(HERE, 'product_list.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for row in reader:
                yield self.search(row['ean'], {
                        'sku': row['model'],
                        'identifier': row['ean'],
                        'name': row['name'],
                        'category': row['category'],
                        'brand': row['brand'],
                        'price': '0.0',
                        })

    def extract_price(self, price):
        """
        override extract price cause French site has different number format: #.###,##
        """
        return extract_price_eu(price)

    def match(self, search_item, new_item): 
        sku = search_item['sku'].lower()
        if sku:
            return (sku in new_item['name'].lower())
        else:
            return (self.match_name(search_item, new_item, match_threshold=70))

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        found_something = False
        matched_any = False
        suggested_product_list = response.meta.get('suggested_search_peek', False)
        meta = response.meta

        for result in hxs.select(u'//div[@id="atfResults" or @id="btfResults"]//div[starts-with(@id, "result_")]'):
            found_something = True
            more_buying_choices = result.select('.//li[@class="sect mbc"]/../li[contains(@class,"mkp2")]/a/@href').extract()
            if more_buying_choices:
                url = urljoin_rfc(get_base_url(response), more_buying_choices[0])
                append_request(url, self.parse_mbc_list, response.meta)
                continue

            try:
                product_name = result.select(u'.//h3/a/span/text()').extract()[0]
            except:
                continue

            try:
                identifier = result.select('./@name').extract()[0]
            except:
                if not result.select('./@id').extract()[0].endswith('_empty'):
                    raise
                continue

            price = result.select('.//span[@class="bld lrg red"]//text()').extract()
            if not price:
                price = result.select('.//span[contains(@class, "price")]//text()').extract()
            if not price:
                self.log('No price on %s' % (response.url))
                continue

            price = self.extract_price(price[0])
            product = Product(response.meta['search_item'])
            product['name'] = product_name
            brand = hxs.select(u'.//h3/span[contains(text(),"by")]/text()').extract()
            if brand:
                product['brand'] = brand[0].replace('by ', '').replace('de ', '').replace('(', '').strip()
            product['price'] = price

            if self._use_amazon_identifier:
                product['identifier'] = product.get('identifier', '') + ':' + identifier
            url = result.select(u'.//h3/a/@href').extract()[0]
            product ['url'] = urljoin_rfc(get_base_url(response), url)
            image_url = result.select(u'.//img[@class="productImage"]/@src').extract()
            if image_url:
                product['image_url'] = urljoin_rfc(get_base_url(response), image_url[0])

            if self.match(response.meta['search_item'], product):
                matched_any = True
                # Go and extract vendor
                meta = dict(response.meta)
                meta['_product'] = product
                append_request(product['url'], self.parse_product, meta)

        # Follow suggested links only on original search page
        if not suggested_product_list and not found_something:
            urls = hxs.select(u'//div[contains(@class,"fkmrResults")]//h3[@class="fkmrHead"]//a/@href').extract()
            if urls:
                self.log('No results found for [%s], trying suggested searches' % (response.meta['search_string']))
            else:
                self.log('No results found for [%s], no suggested searches' % (response.meta['search_string']))

            row = Product(response.meta['search_item']) 
 
            search_term = ''
            if row['sku']:
                search_term = row['brand']+' '+row['sku']
                meta['search_item']['sku_search'] = True
                self.log('No results found for [%s], trying searching by Brand + Model' % (search_term))
            else:
                search_term = row['name'].replace(' ','+')
                self.log('No results found for [%s], trying searching by name' % (search_term))

            search_url = 'http://www.amazon.it/s/ref=nb_sb_noss?url=search-alias%3Daps&field-keywords=' + search_term
            urls.append(search_url)


            for url in urls:
                url = urljoin_rfc(get_base_url(response), url)
                append_request_suggested(url, self.parse_product_list, meta)

        next_url = hxs.select(u'//a[@id="pagnNextLink"]/@href').extract()
        # Follow to next pages only for original search
        # and suggested search if at least one product matched from first page
        # otherwise it tries to crawl the whole Amazon or something like that
        if next_url and (not suggested_product_list or matched_any):
            page = response.meta.get('current_page', 1)
            if self.max_pages is None or page <= self.max_pages:
                response.meta['suggested_search_peek'] = False
                response.meta['current_page'] = page + 1
                url = urljoin_rfc(get_base_url(response), next_url[0])
                append_request(url, self.parse_product_list, response.meta)
            else:
                self.log('Max page limit %d reached' % (self.max_pages))

        for x in self._continue_requests(response):
            yield x

