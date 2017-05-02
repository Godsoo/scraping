# -*- coding: utf-8 -*-

import datetime
import json
import os
import re

import pandas as pd
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter

from product_spiders.utils import extract_price_eu
from product_spiders.config import DATA_DIR
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from sonaeitems import SonaeMeta


HERE = os.path.abspath(os.path.dirname(__file__))


class RadioPopularSpider(BaseSpider):
    name = "sonae-radiopopular.pt"
    allowed_domains = ["radiopopular.pt"]
    start_urls = ['http://www.radiopopular.pt']

    def __init__(self, *args, **kwargs):
        super(RadioPopularSpider, self).__init__(*args, **kwargs)

        self.main_page_parsed = False
        self.meta_df = None

        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if not self.main_page_parsed:
            self.main_page_parsed = True
            request = Request('http://www.radiopopular.pt',
                              dont_filter=True,
                              callback=self.parse)
            self._crawler.engine.crawl(request, self)

    def start_requests(self):
        yield Request('http://www.radiopopular.pt/promocoes/',
                      callback=self.parse_promotions)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response=response)

        categories = hxs.select('//div[@id="nav"]/ul/li/a/@href').extract()
        categories += hxs.select('//div[@id="cat-filtros"]/table/tr/td/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        for product in self.parse_products(response):
            yield product

    def parse_promotions(self, response):
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
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response=response)

        urls = hxs.select('//div[contains(@id, "campanha-")]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url),
                          meta={'exclusive_online': 'Yes'},
                          callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response=response)

        products = hxs.select('//div[@class="produto-dados"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product),
                          meta=response.meta,
                          callback=self.parse_product)

        pages = hxs.select('//div[@id="produtos-paginacao"]/ul/a/li/text()').re('\d+')
        for page in pages:
            yield Request(add_or_replace_parameter(response.url, 'pag', str(page)),
                          callback=self.parse_products)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response=response)
        name = hxs.select('//div[@class="prod-nome"]/text()').extract()
        price = hxs.select('//div[@class="prod-price "]/text()').extract()
        if not price:
            price = hxs.select('//div[@class="prod-price campanha"]/text()').extract()
        price = price[0]

        brand = ''
        categories = hxs.select('//div[@id="breadcrumb"]/ul/li/a/text()').extract()[1:]

        l = ProductLoader(item=Product(), response=response)

        image_url = hxs.select('//div[@id="prod-imagem"]/img/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('name', name)
        l.add_value('price', extract_price_eu(price))
        l.add_value('brand', brand)
        for category in categories:
            l.add_value('category', category)
        ean = hxs.select('//script[@data-flix-ean]/@data-flix-ean').extract()
        l.add_value('sku', ean)
        identifier = re.findall('idprod=(.*)', response.url)[0]
        l.add_value('identifier', identifier)

        product = l.load_item()

        metadata = SonaeMeta()

        promotion_price = hxs.select('//div[@class="prod-price-old"]/del/text()').re(r'[\d,.]+')
        if promotion_price:
            metadata['promotion_price'] = promotion_price[0].replace('.', '').replace(',', '.')

        if response.meta.get('exclusive_online', 'No') == 'Yes':
            metadata['exclusive_online'] = 'Yes'

        if self.meta_df is not None and not self.meta_df.empty and identifier in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier]
        else:
            prev_meta = {}
        promo = hxs.xpath('//div[@id="prod-data"]//div[@class="prod-price campanha"]')
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
