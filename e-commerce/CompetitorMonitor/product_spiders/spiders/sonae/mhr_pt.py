# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4775
Monitor all products. Extract all product options.

"""

import os
import csv
import time
import json
import datetime

import scrapy
import pandas as pd

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from product_spiders.config import DATA_DIR
from sonaeitems import SonaeMeta

class MhrSpider(scrapy.Spider):
    name = 'sonae-mhr.pt'
    allowed_domains = ['mhr.pt']
    start_urls = ('http://www.mhr.pt',)

    def __init__(self, *args, **kwargs):
        super(MhrSpider, self).__init__(*args, **kwargs)
        self.meta_df = None
        self.products = {}

    def _retry(self, response, max_retries=10, sleep_time=10):
        self.log('Sleeping {} seconds'.format(sleep_time))
        time.sleep(sleep_time)
        retries = response.meta.get('retries', 0)
        if retries < max_retries:
            self.log('Retrying URL: {}'.format(response.url))
            return scrapy.Request(response.url,
                                  dont_filter=True,
                                  meta={'retries': retries + 1},
                                  callback=response.request.callback,
                                  priority=-5*(retries+1))
        else:
            self.log('Max retries exceeded: {}'.format(response.url))
            return None

    def parse(self, response):
        if 'SQLSTATE' in response.body:
            retry_req = self._retry(response)
            if retry_req:
                yield retry_req
            else:
                self.log('Error parsing {}'.format(response.url))
            return
        if self.meta_df is None and hasattr(self, 'prev_crawl_id'):
            meta_filename = os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % self.prev_crawl_id)
            if os.path.exists(meta_filename):
                with open(meta_filename) as f:
                    self.meta_df = pd.DataFrame(columns=['identifier', 'promo_start', 'promo_end'], dtype=pd.np.str)
                    for i, line in enumerate(f):
                        p = json.loads(line.strip())
                        self.meta_df.loc[i] = {'identifier': p['identifier'], 'promo_start': p['metadata'].get('promo_start'),
                                               'promo_end': p['metadata'].get('promo_end')}
                    self.meta_df.set_index('identifier', drop=False, inplace=True)
        elif not hasattr(self, 'prev_crawl_id'):
            self.log('prev_crawl_id attr not found')
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            with open(filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.products[row['identifier']] = {'brand': row['brand'].decode('utf8'),
                                                        'category': row['category'].decode('utf8')}
        for url in response.xpath('//*[@id="block_top_menu"]/ul/li/a/@href').extract():
            yield scrapy.Request(response.urljoin(url),
                                 callback=self.parse_categories,
                                 cookies={},
                                 meta={'dont_merge_cookies': True})

    def parse_categories(self, response):
        if 'SQLSTATE' in response.body:
            retry_req = self._retry(response)
            if retry_req:
                yield retry_req
            else:
                self.log('Error parsing {}'.format(response.url))
            return
        for url in response.xpath('//*[@id="subcategories"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url),
                                 callback=self.parse_categories,
                                 cookies={},
                                 meta={'dont_merge_cookies': True})

        '''
        for url in response.xpath('//ul[@class="product_list grid row"]//a[@class="product-name"]/@href').extract():
            yield scrapy.Request(response.urljoin(url),
                                 callback=self.parse_product,
                                 cookies={},
                                 meta={'dont_merge_cookies': True})
        '''
        for product in response.xpath('//div[@class="product-container"]'):
            res = self.extract_product(product)
            if res and 'base64' not in res['image_url']:
                yield res
            else:
                url = product.xpath('.//a[@class="product_img_link"]/@href').extract()[0].split('?')[0]
                yield scrapy.Request(response.urljoin(url),
                                 callback=self.parse_product,
                                 cookies={},
                                 meta={'dont_merge_cookies': True})

        for url in response.xpath('//*[@id="pagination"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url),
                                 callback=self.parse_categories,
                                 cookies={},
                                 meta={'dont_merge_cookies': True})

    def extract_product(self, hxs):
        loader = ProductLoader(Product(), selector=hxs)
        url = hxs.xpath('.//a[@class="product_img_link"]/@href').extract()[0].split('?')[0]
        identifier = url.split('/')[3].split('-')[0]
        if identifier not in self.products:
            return

        price = hxs.xpath('.//span[@itemprop="price"]/text()').extract_first('0')
        price = price.replace(' ', '').replace(',', '.')

        if self.meta_df is not None and not self.meta_df.empty and identifier in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier]
        else:
            prev_meta = {}
        promo = hxs.xpath('.//span[@class="promo-box"]')
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        metadata = SonaeMeta()
        metadata['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            metadata['promo_start'] = promo_start if promo_start and not promo_end else today
            metadata['promo_end'] = ''
        else:
            if promo_start:
                metadata['promo_start'] = promo_start
                metadata['promo_end'] = today if not promo_end else promo_end
        loader.add_xpath('name', './/span[@class="list-name"]/text()')
        loader.add_value('identifier', identifier)
        loader.add_value('url', url)
        loader.add_value('price', price)
        sku = url.split('-')[-1].replace('.html', '')
        try:
            i_sku = int(sku)
            if len(str(sku)) > 10:
                sku = str(sku)
            else:
                sku = ''
        except ValueError:
            sku = ''

        loader.add_value('sku', sku)
        loader.add_xpath('image_url', './/a[@class="product_img_link"]/img/@src')
        stock = hxs.xpath('.//span[@class="avail-label"]/text()').extract_first()
        if not stock:
            loader.add_value('stock', 0)
        loader.add_value('brand', self.products[identifier]['brand'])
        loader.add_value('category', self.products[identifier]['category'])
        item = loader.load_item()
        item['metadata'] = metadata
        return item

    def parse_product(self, response):
        if 'SQLSTATE' in response.body:
            retry_req = self._retry(response)
            if retry_req:
                yield retry_req
            else:
                self.log('Error parsing {}'.format(response.url))
            return

        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract_first()
        identifier = response.xpath('//*[@id="product_page_product_id"]/@value').extract_first()
        image_url = response.xpath('//*[@id="bigpic"]/@src').extract_first()
        price = response.xpath('//*[@id="our_price_display"]/text()').extract_first('0')
        sku = response.xpath('//label[text()="EAN "]/../span/text()').extract_first()
        brand = response.xpath('//label[text()="Fabricante "]/../span/text()').extract_first()
        categories = response.xpath('//div[@class="breadcrumb clearfix"]//a/text()').extract()
        stock = response.xpath('//span[@class="avail-label"]/text()').extract_first()
        loader.add_value('name', name)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('brand', brand)
        loader.add_value('category', categories)
        loader.add_value('url', response.url)
        if image_url and not image_url.strip().startswith('data:image'):
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('price', extract_price(price.replace(' ', '')))
        if not stock:
            loader.add_value('stock', 0)
        item = loader.load_item()

        if self.meta_df is not None and not self.meta_df.empty and identifier in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier]
        else:
            prev_meta = {}
        promo = response.xpath('//p[@id="reduction_amount" and not(contains(@style,"display:none"))]'
                               '/span[@id="reduction_amount_display" and text()!=""]')
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        metadata = SonaeMeta()
        metadata['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            metadata['promo_start'] = promo_start if promo_start and not promo_end else today
            metadata['promo_end'] = ''
        else:
            if promo_start:
                metadata['promo_start'] = promo_start
                metadata['promo_end'] = today if not promo_end else promo_end
        item['metadata'] = metadata
        yield item
