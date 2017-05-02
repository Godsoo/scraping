# -*- coding: utf-8 -*-
"""
Account: Transcat
Name: transcat-transcat.com
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4822
Extract the products from the URL’s in row E.

Original developer: Franco Almonacid <fmacr85@gmail.com>
"""


import re
import os
import csv
import json

from scrapy import Spider, FormRequest, Request
from product_spiders.items import (
    ProductLoaderWithNameStrip as ProductLoader,
    Product,
)

from product_spiders.utils import extract_price
from product_spiders.lib.schema import SpiderSchema
from transcatitems import TranscatMeta
from cStringIO import StringIO
from product_spiders.config import DATA_DIR

HERE = os.path.abspath(os.path.dirname(__file__))


class TranscatSpider(Spider):
    name = 'transcat-transcat.com'
    allowed_domains = ['transcat.com']

    filename = os.path.join(HERE, 'Transcatfeed.csv')
    start_urls = ('file://' + filename,)


    def parse(self, response):
        self.prev_strikes = dict()
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, 'meta/%s_meta.json-lines' % self.prev_crawl_id)
            
            with open(filename) as f:
                for row in f:
                    data = json.loads(row)
                    self.prev_strikes[data['identifier']] = data['metadata'].get('strike')
                    
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            yield Request(response.urljoin(row['URL']), callback=self.parse_product, meta={'row': row})
       
    def parse_product(self, response):
        data = SpiderSchema(response).get_product()

        row = response.meta['row']

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0]

        identifier = response.xpath('//div[@class="product-view"]//input[@name="product"]/@value').extract()
        if not identifier:
            identifier = response.xpath('//a[@title="Email"]/@href').re('id\/(\d+)')
        identifier = identifier[0]

        sku = row['Transcat SKU']
        strike = None
        price = response.css('div.product-type-data p.special-price').xpath('span[@itemprop="price"]/text()').extract()
        if not price:
            price = response.css('div.product-type-data span.nobr').xpath('span[@itemprop="price"]/text()').extract()
        #price = extract_price(price[0]) if price else '0'
        if type(data.get('offers')) == list:
            price = data['offers'][0]['properties']['price']
        else:
            try:
                price = data['offers']['properties']['price']
            except KeyError:
                price = 0
        if type(price) == list:
            strike = price[0]
            price = price[-1]
            if response.meta.get('retries'):
                self.logger.debug('Helped!')
        else:
            retries = response.meta.get('retries', 0)
            if retries < 2:
                meta = response.meta.copy()
                meta['retries'] = retries + 1
                yield Request(response.url,
                              self.parse_product,
                              dont_filter=True,
                              meta=meta)
                return
            if self.prev_strikes[identifier]:
                self.logger.debug('No strike price more on %s' % response.url)
                fname = os.path.join(DATA_DIR, '../logs/default/transcat-transcat.com/%s.html' % response.url.split('/')[-1])
                with open(fname, 'w') as f:
                    f.write(response.body)
                
        product_image = response.xpath('//img[@id="image"]/@src').extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        loader.add_value('price', 0)

        if product_image:
            loader.add_value('image_url', product_image[0])
        loader.add_value('brand', row['Brand'].decode('utf'))
        categories = row['Category'].split(',')
        categories = map(lambda x: x.decode('utf'), categories)
        loader.add_value('category', categories)

        stock = response.xpath('//p[@class="availability in-stock"]')
        if stock:
            stock = stock.select('span[@class="product-qty"]').re('\d+')
            loader.add_value('stock', int(stock[0]))

        out_of_stock = response.xpath('//p[@class="special-text-msg" and contains(text(), "not available")]')
        if out_of_stock:
            loader.add_value('stock', 0)

        item = loader.load_item()
        metadata = TranscatMeta()
        mpn = response.xpath('//p[@itemprop="mpn"]/text()').re('Mfg Part #: (.*)')
        metadata['mpn'] = mpn[0].strip() if mpn else ''
        #strike = response.xpath('//div[@class="product-type-data"]//p[@class="old-price"]/span[@itemprop="price"]/text()').extract_first()
        metadata['strike'] = strike.strip() if strike else ''

        item['metadata'] = metadata

        yield item

