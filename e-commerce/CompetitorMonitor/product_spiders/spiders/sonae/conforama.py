# -*- coding: utf-8 -*-

import json
import datetime
import os.path
from copy import deepcopy

from scrapy import Spider, Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import pandas as pd

from product_spiders.utils import extract_price_eu
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from product_spiders.config import DATA_DIR
from product_spiders.spiders.sonae.sonaeitems import SonaeMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class ConforamaSpider(Spider):
    name = "sonae-conforama.pt"
    allowed_domains = ["conforama.pt"]
    start_urls = ['http://www.conforama.pt']

    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0'
    meta_df = None
    identifiers = []

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
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//div[@id="main-menu"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_cat)

    def parse_cat(self, response):
        base_url = get_base_url(response)
        products = response.css('div#listing div.product-container > a')
        for prod_el in products:
            url = prod_el.xpath("@href").extract_first()
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        for next_page_url in response.css("ul.pagination li a").xpath("@href").extract():
            yield Request(urljoin_rfc(base_url, next_page_url), callback=self.parse_cat)

    def parse_product(self, response):
        name = response.xpath("//@data-gtm-detail-name").extract_first()

        price = extract_price_eu(response.xpath("//@data-gtm-detail-price").extract_first())

        identifier = response.xpath("//@data-gtm-detail-id").extract_first()
        sku = identifier

        brand = response.xpath("//@data-gtm-detail-brand").extract_first()

        categories = response.xpath("//@data-gtm-detail-category").extract_first().replace('/', ' > ')

        image_url = response.xpath("//a[@id='ma-zoom1']/img/@src").extract_first()

        promotion = response.css('div.prod-price-inner span s').xpath("text()").extract_first()
        promotion = str(extract_price_eu(promotion)) if promotion else ''

        l = ProductLoader(item=Product(), response=response)

        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('brand', brand)
        l.add_value('category', categories)
        l.add_value('identifier', identifier)
        l.add_value('sku', sku)

        item = l.load_item()
        metadata = SonaeMeta()
        metadata['promotion_price'] = promotion

        if self.meta_df is not None and not self.meta_df.empty and identifier in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier]
        else:
            prev_meta = {}
        promo = promotion
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

        item['metadata'] = metadata

        options_config = response.css('select#configurable-picker')
        if options_config:
            for option in options_config.css('option'):
                new_item = deepcopy(item)
                new_identifier = option.xpath('@data-itemreference').extract_first()
                new_item['name'] += ' ' + option.xpath('text()').extract_first()
                new_item['identifier'] = new_identifier
                new_item['sku'] = new_identifier
                new_item['price'] = extract_price_eu(option.xpath('@data-priceafter').extract_first())
                new_item['image_url'] = response.xpath('//li[@data-itemreference="' + new_identifier + '"]/@data-large-url').extract_first()
                yield new_item
        else:
            if item['identifier'] not in self.identifiers:
                self.identifiers.append(item['identifier'])
                yield item
