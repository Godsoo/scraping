# -*- coding: utf-8 -*-
import datetime
import json
import os
from urlparse import urljoin as urljoin_rfc

import pandas as pd
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter

from product_spiders.config import DATA_DIR
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from sonaeitems import SonaeMeta

class GamingreplaySpider(BaseSpider):
    name = 'sonae-gamingreplay.com'
    allowed_domains = ['gamingreplay.com']
    start_urls = ('https://www.gamingreplay.com',)
    download_delay = 2
    meta_df = None

    def parse(self, response):
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
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        urls = hxs.select('//*[@id="cbp-hrmenu"]/ul//li/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_products_list,
                          cookies={},
                          meta={'dont_merge_cookies': True})

    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        show_all = hxs.select('//form[@class="showall"]')
        if show_all:
            show_all = show_all[0]
            url = show_all.select('./@action').extract()[0]
            id_category = show_all.select('.//input[@name="id_category"]/@value').extract()[0]
            n = show_all.select('.//input[@name="n"]/@value').extract()[0]
            url = add_or_replace_parameter(url, 'id_category', id_category)
            url = add_or_replace_parameter(url, 'n', n)
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_products_list,
                          cookies={},
                          meta={'dont_merge_cookies': True})
        else:
            urls = hxs.select('//*[@id="pagination"]//a/@href').extract()
            for url in urls:
                yield Request(urljoin_rfc(base_url, url),
                              callback=self.parse_products_list,
                              cookies={},
                              meta={'dont_merge_cookies': True})
            urls = hxs.select('//ul[@class="product_list grid row"]//a[@class="product-name"]/@href').extract()
            for url in urls:
                yield Request(urljoin_rfc(base_url, url),
                              callback=self.parse_product,
                              cookies={},
                              meta={'dont_merge_cookies': True})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        price = hxs.select('//*[@id="our_price_display"]/text()').extract()
        price = extract_price(price[0])
        product_loader.add_value('price', price)
        identifier = hxs.select('//*[@id="product_page_product_id"]/@value').extract()[0]
        product_loader.add_value('identifier', identifier)
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        product_loader.add_value('name', name)
        product_loader.add_value('sku', identifier)
        image_url = hxs.select('//*[@id="bigpic"]/@src').extract()
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        category = hxs.select('//div[@class="breadcrumb clearfix"]//a[not(@class)]/text()').extract()
        product_loader.add_value('category', category)
        product_loader.add_value('url', response.url)
        stock = hxs.select('//*[@id="availability_value"]/text()').extract()
        if stock and stock[0] == u'Este produto não se encontra em stock':
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        metadata = SonaeMeta()
        if self.meta_df is not None and not self.meta_df.empty and identifier in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier]
        else:
            prev_meta = {}
        promo = response.xpath('//p[@id="reduction_amount" and not(contains(@style,"display:none"))]'
                               '/span[@id="reduction_amount_display" and text()!=""]')
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        metadata['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            metadata['promo_start'] = promo_start if promo_start and not promo_end else today
            metadata['promo_end'] = ''
        else:
            if promo_start:
                metadata['promo_start'] = promo_start
                metadata['promo_end'] = today if not promo_end else promo_end
        product['metadata'] = metadata
        yield product
