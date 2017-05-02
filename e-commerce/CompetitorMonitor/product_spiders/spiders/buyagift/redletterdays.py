# -*- coding: utf-8 -*-

import re
import json

from scrapy import Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.utils.url import add_or_replace_parameter
from product_spiders.lib.spiderdata import SpiderData
from product_spiders.items import Product, ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider


class RedletterdaysCoUkSpider(PrimarySpider):
    name = u'redletterdays.co.uk'
    allowed_domains = ['www.redletterdays.co.uk']
    start_urls = [
        'https://www.redletterdays.co.uk/search?q='
    ]

    csv_file = 'redletterdays.co.uk_products.csv'

    def __init__(self, *args, **kwargs):
        super(RedletterdaysCoUkSpider, self).__init__(*args, **kwargs)

        self._previous_categories = {}
        self._close_spider = False
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def _load_previous_categories(self):
        sd = SpiderData(spider_name=self.name)
        f, reader = sd.get_prev_crawl_data_reader()
        for row in reader:
            self._previous_categories[row['identifier'].lower()] = row['category']

    def spider_idle(self, spider, *args, **kwargs):
        if not self._close_spider:
            self._close_spider = True
            req = Request(self.start_urls[0],
                          callback=self.parse_all,
                          dont_filter=True)
            self.crawler.engine.crawl(req, self)

    def parse_all(self, response):
        self._load_previous_categories()
        for r in self.parse_category(response):
            yield r

    def parse(self, response):
        categories = response.xpath('//div[@id="categoryFilterPanel"]//a')
        for cat in categories:
            cat_name = cat.xpath('span/text()').extract()[0]
            cat_id = cat.xpath('@data-bind').re(r'\d+')[0]
            cat_url = add_or_replace_parameter(response.url, 'cat', str(cat_id))
            cat_url = add_or_replace_parameter(cat_url, 'p', '1')
            yield Request(cat_url, callback=self.parse_category,
                          meta={'category': cat_name, 'page': 1})

    def parse_category(self, response):
        json_data = re.findall(r'"ProductTileModels":(\[.*\])?,"SideBarSubSectionModel"', response.body)[0]
        products = json.loads(json_data)
        for product in products:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', product['BrochureDescription'])
            loader.add_value('url', response.urljoin(product['Url']))
            loader.add_value('image_url', product['ImageUrl'])
            if 'category' in response.meta:
                loader.add_value('category', response.meta['category'])
            elif product['ExpRef'].lower() in self._previous_categories:
                loader.add_value('category', self._previous_categories[product['ExpRef'].lower()])
            loader.add_value('price', product['Price'])
            loader.add_value('identifier', product['ExpRef'])
            loader.add_value('sku', product['ExpRef'])
            yield loader.load_item()

        if products:
            next_page = response.meta.get('page', 1) + 1
            new_meta = response.meta.copy()
            new_meta['page'] = next_page
            yield Request(add_or_replace_parameter(response.url, 'p', str(next_page)),
                          callback=self.parse_category,
                          meta=new_meta)
