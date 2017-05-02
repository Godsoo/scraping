# -*- coding: utf-8 -*-

import json
import scrapy
import os
import datetime

import pandas as pd
from scrapy.utils.url import url_query_parameter

from sonaeitems import SonaeMeta
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import DATA_DIR


class PhonehouseSpider(scrapy.Spider):
    name = 'sonae-phonehouse.pt'
    allowed_domains = ['phonehouse.pt']
    start_urls = ('http://www.phonehouse.pt',)

    def __init__(self, *args, **kwargs):
        super(PhonehouseSpider, self).__init__(*args, **kwargs)
        self.meta_df = None

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
        for url in response.xpath('//*[@id="header"]/nav/div/ul/li/a/@href').extract():
            u_id = url_query_parameter(url, 'id')
            u_cat = url_query_parameter(url, 'cat')
            if u_id and u_cat:
                yield scrapy.Request('http://www.phonehouse.pt/api.php/getProducts/' + u_id + '/' + u_cat + '/0',
                                     callback=self.parse_products,
                                     meta={'u_id': u_id, 'u_cat': u_cat, 'offset': 0})

    def parse_products(self, response):
        data = json.loads(response.body)
        products = data['response']['products']
        if products:
            u_id = response.meta['u_id']
            u_cat = response.meta['u_cat']
            offset = response.meta['offset']
            for product in products:
                product_loader = ProductLoader(item=Product(), response=response)
                if product['price']:
                    product_loader.add_value('identifier', product['id'])
                    product_loader.add_value('name', product['title'])
                    product_loader.add_value('sku', product['id'])
                    price = product['price']['value'].replace(' ', '').replace('.', '').replace(',', '.')
                    product_loader.add_value('price', price)
                    product_loader.add_value('image_url', response.urljoin(product['featured_image']['source']))
                    product_loader.add_value('url', product['url'])
                    product_loader.add_value('brand', product['brand']['name'])
                    if product['variants'][0]['inventory_quantity'] == '0':
                        product_loader.add_value('stock', 0)
                    product_loader.add_value('category', product['category'])
                    exclusive_online = False
                    metadata = SonaeMeta()
                    promo = False
                    for tag in product['tags']:
                        if u'promo' in tag['title'].lower():
                            promo = True
                        if u"PromoçãoOnline" in tag['title'].title().replace(' ', ''):
                            exclusive_online = True

                    if self.meta_df is not None and not self.meta_df.empty and product['id'] in self.meta_df.index:
                        prev_meta = self.meta_df.loc[product['id']]
                    else:
                        prev_meta = {}
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
                    if exclusive_online:
                        metadata['exclusive_online'] = 'Yes'
                    item = product_loader.load_item()
                    item['metadata'] = metadata
                    yield item

            yield scrapy.Request('http://www.phonehouse.pt/api.php/getProducts/' + u_id + '/' + u_cat + '/' + str(offset + 12),
                                 callback=self.parse_products,
                                 meta={'u_id': u_id, 'u_cat': u_cat, 'offset': offset + 12})
