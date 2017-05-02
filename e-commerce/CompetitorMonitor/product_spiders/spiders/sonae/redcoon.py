# -*- coding: utf-8 -*-
import datetime
import json
import os
from urlparse import urljoin as urljoin_rfc

import pandas as pd
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.config import api_key, new_system_api_roots

from product_spiders.config import DATA_DIR
from product_spiders.utils import extract_price_eu as extract_price, get_cm_api_root_for_spider
from sonaeitems import SonaeMeta


class RedcoonSpider(BaseSpider):
    name = u'sonae-redcoon.pt'
    allowed_domains = ['www.redcoon.pt']
    start_urls = ('http://www.redcoon.pt/',)

    def __init__(self, *args, **kwargs):
        super(RedcoonSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        dispatcher.connect(self.spider_opened, signals.spider_opened)
        self.meta_df = None
        self.products_extracted = False

    def spider_opened(self):
        compmon_host = get_cm_api_root_for_spider(self)
        compmon_host = compmon_host.split(":")[-2].replace('//', '')
        if compmon_host not in self.allowed_domains:
            self.allowed_domains.append(compmon_host)

    def spider_idle(self, spider):
        if not self.products_extracted and spider.name == self.name:
            self.products_extracted = True
            all_products_url = '%(api_root)s/api/get_all_products_website.json?website_id=%(website_id)s&offset={}&limit=1000&api_key=%(api_key)s' % {
                'api_root': get_cm_api_root_for_spider(self),
                'website_id': self.website_id,
                'api_key': api_key
            }
            request = Request(all_products_url.format('0'),
                              dont_filter=True,
                              callback=self.parse_all_products, meta={'next_offset': 1000, 'all_products_url': all_products_url})
            self._crawler.engine.crawl(request, self)
            raise DontCloseSpider

    def parse_all_products(self, response):
        products = json.loads(response.body)['products']
        for product in products:
            yield Request(product['url'], callback=self.parse_product)

        if products:
            meta = response.meta
            next_offset = int(meta.get('next_offset'))
            all_products_url = meta.get('all_products_url').format(str(next_offset))
            meta['next_offset'] = next_offset + 1000
            yield Request(all_products_url, dont_filter=True, callback=self.parse_all_products, meta=meta)

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
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="startnav"]/li//li[not(@class="title")]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category, meta={'dont_redirect': True})

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="leftC"]//li[contains(@class,"level3")]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta={'dont_redirect': True})

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//*[@id="productpool"]/li//h2/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'dont_redirect': True})
        for url in hxs.select('//span[@class="pagelinks"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta={'dont_redirect': True})

    def parse_product(self, response):
        base_url = get_base_url(response)

        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@class="stretch clearfix box"]/select/option/@value').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'dont_redirect': True})
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//*[@id="centerC"]/h1/span[@itemprop="name"]/text()').extract()[0]
        loader.add_value('name', name)
        identifier = hxs.select('//div[@class="pd-container-right"]//form[@class="addBasketItem"]//input[@name="productId"]/@value').extract()
        if not identifier:
            return
        loader.add_value('identifier', identifier[0])
        loader.add_value('url', response.url)
        price = hxs.select('//noscript/span/text()').extract()
        price = extract_price(price[0]) if price else '0'
        loader.add_value('price', price)
        stock = hxs.select('//*[@id="first3"]/p/span/text()').extract()
        stock = stock[0] if stock else ''
        categories = hxs.select('//*[@id="infoblock"]/div/a/text()').extract()[1:]
        for category in categories:
            loader.add_value('category', category)
        brand = hxs.select('//div[@class="pd-brand box"]/a/img/@alt').extract()
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)
        image_url = hxs.select('//*[@id="showPic"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        product = loader.load_item()

        promotion_price = hxs.select(u'//p[contains(text(), "Preço Regular")]/strike/text()').re(r'[\d,.]+')
        metadata = SonaeMeta()
        metadata['exclusive_online'] = 'No'
        if promotion_price:
            metadata['promotion_price'] = promotion_price[0].replace('.', '').replace(',', '.')
        metadata['stock'] = stock

        if self.meta_df is not None and not self.meta_df.empty and identifier[0] in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier[0]]
        else:
            prev_meta = {}
        promo = promotion_price
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

        shipping_pid = hxs.select('//span[@id="shipmentDetails"]/@data-productid').extract()
        if shipping_pid:
            shipping_url = 'https://www.redcoon.pt/req/ajax/mod/ShopShipment/pid/' + shipping_pid[0]
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
            }
            yield Request(shipping_url, headers=headers, callback=self.parse_shipping,
                          meta={'product': product})
        else:
            yield product

    def parse_shipping(self, response):
        product = response.meta['product']

        data = json.loads(response.body)
        hxs = HtmlXPathSelector(text=data['html'])

        shipping = hxs.select('//span[@class="right"]').re(r'[\d,.]+')
        if shipping:
            product['shipping_cost'] = extract_price(shipping[0])

        yield product
