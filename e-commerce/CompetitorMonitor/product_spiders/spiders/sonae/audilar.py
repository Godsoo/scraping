# -*- coding: utf-8 -*-
"""
Customer: Worten
Website: http://audilar.pt
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4776
Monitor all products. Extract all product options.


"""
import datetime
import json
import os
import re

import pandas as pd
from scrapy.spider import BaseSpider
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter
from scrapy.http import Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import DATA_DIR
from product_spiders.utils import extract_price_eu as extract_price
from sonaeitems import SonaeMeta


class AudilarSpider(BaseSpider):
    name = 'sonae-audilar.pt'
    allowed_domains = ['audilar.pt']
    start_urls = ('http://audilar.pt/',)

    rotate_agent = True
    meta_df = None

    #download_delay = 4

    already_scraped = []

    def start_requests(self):
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
        dispatcher.connect(self.my_spider_idle, signals.spider_idle)
        yield Request('http://audilar.pt/promocoes',
                      meta={'promo': True})

    def my_spider_idle(self, spider):
        if spider.name == self.name:
            self.log('Spider idle parsing homepage')
            for url in self.start_urls:
                req = Request(url)
                self._crawler.engine.crawl(req, self)

    def parse(self, response):
        categories = response.xpath('//ul[contains(@class, "mainmenu megamenu")]//a/@href').extract()
        for category in categories:
            url = response.urljoin(category)
            yield Request(url, meta=response.meta)

        next_page = response.xpath('//div[@class="pagination"]//a[text()=">"]/@href').extract()
        if next_page:
            next_page = response.urljoin(next_page[0])
            yield Request(next_page, meta=response.meta)

        products = response.xpath('//div[contains(@class, "box-product")]//div[@class="name"]/a/@href').extract()
        for product in products:
            product_page = product.split('/')[-1]
            if product_page not in self.already_scraped:
                self.already_scraped.append(product_page)
                yield Request(response.urljoin(product), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        product_loader = ProductLoader(item=Product(), response=response)
        price = response.xpath('//div[@class="product-info"]//span[@class="price-fixed"]/text()').extract()[0]
        price = extract_price(price)
        product_loader.add_value('price', price)
        identifier = response.xpath('//input[@name="product_id"]/@value').extract()[0]
        product_loader.add_value('identifier', identifier + '-new')
        name = response.xpath('//div[@class="product-info"]//h1/text()').extract_first()
        product_loader.add_value('name', name)

        sku = response.xpath('//div[@class="description"]'
                             '/span[contains(text(), "digo do produto")]'
                             '/following-sibling::text()[1]').extract()[0].strip()
        product_loader.add_value('sku', sku)

        brand = response.xpath('//div[@class="description"]'
                               '/span[contains(text(), "Fabricantes")]'
                               '/following-sibling::a[1]/text()').extract()
        brand = brand[0].strip() if brand else ''
        product_loader.add_value('brand', brand)

        stock_text = response.xpath('//div[@class="description"]'
                                    '/span[contains(text(), "Disponibilidade")]'
                                    '/following-sibling::text()[1]').extract()[0].strip()
        stock = u'Dispon\xedvel para Encomenda' in stock_text
        if not stock:
            product_loader.add_value('stock', 0)

        image_url = response.xpath('//div[@class="product-info"]//div[contains(@class, "image")]/a/@href').extract()
        if image_url:
            product_loader.add_value('image_url', image_url[0])
        category = response.xpath('//div[@class="breadcrumb"]/a/text()').extract()[1:-1]
        product_loader.add_value('category', category)
        product_loader.add_value('url', response.url)
        product = product_loader.load_item()
        product['metadata'] = SonaeMeta()

        lookup_id = identifier + '-new'
        if self.meta_df is not None and not self.meta_df.empty and lookup_id in self.meta_df.index:
            prev_meta = self.meta_df.loc[lookup_id]
        else:
            prev_meta = {}

        promo = response.meta.get('promo', False)
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        product['metadata']['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            product['metadata']['promo_start'] = promo_start if promo_start and not promo_end else today
            product['metadata']['promo_end'] = ''
        else:
            if promo_start:
                product['metadata']['promo_start'] = promo_start
                product['metadata']['promo_end'] = today if not promo_end else promo_end

        yield product

