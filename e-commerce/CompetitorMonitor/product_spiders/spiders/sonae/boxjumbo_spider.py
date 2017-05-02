# -*- coding: utf-8 -*-
import datetime
import os
import json
import re

import pandas as pd
from scrapy.spider import BaseSpider
from scrapy.http import Request, FormRequest

from product_spiders.config import DATA_DIR
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price
from sonaeitems import SonaeMeta

here = os.path.abspath(os.path.dirname(__file__))

class BoxjumboSpider(BaseSpider):
    name = "sonae-boxjumbo.pt"
    allowed_domains = ["jumbo.pt"]
    start_urls = ["https://www.jumbo.pt/", "https://www.jumbo.pt/Frontoffice/"]
    meta_df = None

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
            yield Request(url, dont_filter=True)

    def parse(self, response):

        categories = response.xpath('//div[@class="main-menu-wrapper"]//a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category))

        products = response.xpath('//div[@class="product-item-header"]/a/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        if products:
            meta = response.meta
            pagination_url = response.url
            if '/pagination' not in response.url:
                pagination_url = response.url + '/pagination'

            page = meta.get('page', 0) + 1
            meta['page'] = page

            if not meta.get('cat_filter', None):
                meta['cat_filter'] = ''.join(response.xpath('//div[@data-filterparamname="CategoryFriendlyName"]/@data-filterparamvalue').extract())
                meta['market_filter'] = ''.join(response.xpath('//div[@data-filterparamname="MarketFriendlyName"]/@data-filterparamvalue').extract())
                meta['segment_filter'] = ''.join(response.xpath('//div[@data-filterparamname="SegmentFiendlyName"]/@data-filterparamvalue').extract())
            
 
            data = {"CategoryFriendlyName": meta['cat_filter'],
                    "CurrentPage": str(page),
                    "Id": "",
                    "MarketFriendlyName": meta['market_filter'],
                    "PageSize": 15,
                    "SegmentFiendlyName": meta['segment_filter'],
                    "SortingDirection": 1,
                    "SortingType": 2}

            req = FormRequest(pagination_url, 
                              dont_filter=True, 
                              method='POST',
                              body=json.dumps(data), 
                              headers={'Content-Type':'application/json'}, 
                              meta=meta)
            yield req

    def parse_product(self, response):
        l = ProductLoader(item=Product(), response=response)
        metadata = SonaeMeta()

        l.add_xpath('image_url', '//img[contains(@class, "product-detail-img-main")]/@src')
        l.add_value('url', response.url)
        name = response.xpath('//h1/text()').extract()[0].strip()
        #name_desc = ''.join(hxs.select('//span[@class="infoDet"]/text()').extract()).strip()
        #l.add_value('name', name + ' ' + name_desc)
        l.add_value('name', name)
        price = ''.join(response.xpath('//span[@class="item-price"]/text()').extract()[0].strip().split())
        l.add_value('price', extract_price(price))
 
        out_of_stock = response.xpath(u'//div[@class="product-btns-panel"]/button[contains(text(), "Indisponível")]')
        if out_of_stock:
            l.add_value('stock', 0)

        categories = response.xpath('//ol[@class="breadcrumb"]/li/a/text()').extract()[1:]
        for category in categories:
            l.add_value('category', category)
        
        brand = response.xpath('//div[h1]/h3/text()').extract()
        if brand:
            l.add_value('brand', brand[0])
        '''
        weight = response.xpath('//div[h2[contains(text(), "Peso")]]/p/text()').extract()
        if not weight:
            weight = response.xpath('//tr[td[contains(text(), "Peso")]]/td/@txt').extract()
        
        weight = extract_price(weight[0]) if weight else 0
        shipping = 0
        if weight>=0.5 and weight<3:
            shipping = 2
        if weight>=3 and weight<5:
            shipping = 4
        if weight>=5 and weight<10:
            shipping = 5
        if weight>=10 and weight<20:
            shipping = 10
        if weight>=20:
            shipping = 15
                
        if shipping:
            l.add_value('shipping_cost', shipping)
        '''
        identifier = response.xpath('//input[@name="Id"]/@value').extract()
        l.add_value('identifier', identifier[0])
        l.add_value('sku', identifier[0])

        if self.meta_df is not None and not self.meta_df.empty and identifier[0] in self.meta_df.index:
            prev_meta = self.meta_df.loc[identifier[0]]
        else:
            prev_meta = {}
        promo = response.xpath('//span[@class="item-old-price"]/span[@class="item-old-price"]/text()')
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

        item = l.load_item()
        item['metadata'] = metadata
        yield item
