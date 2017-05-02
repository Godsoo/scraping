# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import os
import csv
import cStringIO

from scrapy.http import Request
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from base_spiders.target.targetspider import BaseTargetSpider

HERE = os.path.abspath(os.path.dirname(__file__))


class TargetTestSpider(BaseTargetSpider):
    name = 'hamiltonbeach-target.com'
    start_urls = ('http://www.target.com/bp/keurig',)

    def __init__(self, *args, **kwargs):
        super(TargetTestSpider, self).__init__(*args, **kwargs)

        self.urls = []

        with open(os.path.join(HERE, 'brands.csv')) as f:
            for i, brand in enumerate(f):
                brand_cleaned = brand.strip()
                search_url = 'http://tws.target.com/searchservice/item/search_results/v2/by_keyword?search_term=%s&alt=json&pageCount=900000&response_group=Items&zone=mobile&offset=0'
                brand_search = brand_cleaned.lower().replace(' ', '+').replace('&', 'and')
                url = {'url':search_url % (brand_search), 'brand': brand_cleaned}
                self.urls.append(url)

        with open(os.path.join(HERE, 'target_productsearch.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for i, row in enumerate(reader):
                code_search = row['TCIN'].strip()
                search_url = 'http://tws.target.com/searchservice/item/search_results/v2/by_keyword?search_term=%s&alt=json&pageCount=900000&response_group=Items&zone=mobile&offset=0'
                url = {'url':search_url % (code_search), 'brand': row["Brand Name"].strip()}
                self.urls.append(url)

        self.brands = [x['brand'] for x in self.urls]

        self.data = {}
        self.found_ids = set()
        with open(os.path.join(HERE, 'target.com_products.csv')) as f:
            reader = csv.DictReader(cStringIO.StringIO(f.read()))
            for i, row in enumerate(reader):
                self.data[row['target_number']] = row['sku']
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.all_data_checked = False

    def spider_idle(self, spider):
        """
        Runs after all pages and items processed but before closing
        Populates all 'out of stock' items as they were just stored in attribute
        """
        self.log("Spider idle")

        # search for identifiers which are not collected

        if spider.name == self.name and not self.all_data_checked:
            f = open(os.path.join(HERE, 'target_products.csv'))
            reader = csv.reader(f)
            for row in reader:
                url = row[0]
                sku = row[1]
                request = Request(url, dont_filter=True, callback=self.parse_product, meta={'sku': sku})
                self._crawler.engine.crawl(request, self)
        self.all_data_checked = True

    def start_requests(self):
        for url in self.urls:
            yield Request(url['url'], meta={'brand': url['brand']})

    def parse_product_json(self, response):
        try:
            request = super(TargetTestSpider, self).parse_product_json(response).next()
        except StopIteration:
            return
        product = request.meta.get('product')
        if product:
            self.found_ids.add(product['identifier'])
            if product.get('sku', '') == '':
                product['sku'] = self.data.get(product['identifier'], '')
            if product['brand'] == '':
                for pos_brand in self.brands:
                    if pos_brand.lower() in ' '.join(product['name']).lower():
                        product['brand'] = pos_brand
                        break
            product['price'] = 0
            request.meta['product'] = product
        yield request
