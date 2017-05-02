# -*- coding: utf-8 -*-
import csv
import json
import os
import urlparse
import re
import hashlib
from scrapy.spider import BaseSpider
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from urlparse import urljoin as urljoin_rfc
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.config import DATA_DIR

HERE = os.path.abspath(os.path.dirname(__file__))


class DigiDirectSpider(BaseSpider):
    name = 'digidirect'
    allowed_domains = ['digidirect.com.au', 'studio19.com.au']
    start_urls = ['http://www.digidirect.com.au']
    collected_urls = set()

    def __init__(self, *args, **kwargs):
        super(DigiDirectSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        self.log('SPIDER IDLE')
        if spider.name == self.name:
            if hasattr(self, 'prev_crawl_id'):
                data_file = os.path.join(DATA_DIR, '{}_products.csv'.format(self.prev_crawl_id))
                with open(data_file) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        req = Request(row['url'],
                                      meta={'category': row['category']},
                                      callback=self.parse_product)
                        self.crawler.engine.crawl(req, self)

    def parse(self, response):
        # we extract the categories urls
        categories = response.xpath('//div[contains(@class, "category-slide-container")]//a/@href').extract()
        categories += response.xpath('//div[@class="footer_links"]//a/@href').extract()
        for category in categories:
            yield Request(
                urlparse.urljoin(response.url, category),
                callback=self.parse_category
            )

    def parse_category(self, response):
        product_category = ''.join(response.xpath("//div[contains(@class, 'product-header')]//h1/text()").extract())
        cat = re.search('page_id": "([^"]*)"', response.body)
        if cat:
            cat = cat.group(1)
        else:
            return

        yield FormRequest(
            'http://www.digidirect.com.au/Shopping/Search/viewMore',
            formdata={
                'category[]': cat,
                'from': str(0),
                'viewtype': 'list',
                'sortby': 'name_asc',
                'minprice': '0',
                'maxprice': '9999999',
            },
            headers={'X-Requested-With': 'XMLHttpRequest', 'X-Request': 'JSON'},
            meta={
                'category': product_category,
                'category[]': cat,
                'from': 0,
            },
            callback=self.parse_category2,
        )

    def parse_category2(self, response):
        data = json.loads(response.body)
        sel = Selector(text=data['productlist'])

        n = 0
        products = set(sel.xpath('//li[contains(@class, "product-list-view")]/div/a/@href').extract())
        for url in products:
            if url in self.collected_urls:
                continue
            self.collected_urls.add(url)
            n += 1
            yield Request(
                urljoin_rfc(self.start_urls[0], url),
                meta={
                    'category': response.meta['category'],
                },
                callback=self.parse_product
            )
        self.log('Got %d items' % n)
        if len(products) > 0:
            from_ = response.meta['from'] + 15
            yield FormRequest(
                'http://www.digidirect.com.au/Shopping/Search/viewMore',
                formdata={
                    'category[]': response.meta['category[]'],
                    'from': str(from_),
                    'viewtype': 'list',
                    'sortby': 'name_asc',
                    'minprice': '0',
                    'maxprice': '9999999',
                    'from_scroll': 'true',
                },
                headers={'X-Requested-With': 'XMLHttpRequest', 'X-Request': 'JSON'},
                meta={
                    'category': response.meta['category'],
                    'category[]': response.meta['category[]'],
                    'from': from_,
                },
                callback=self.parse_category2,
            )

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)

        price = response.xpath('//*[@class="mainprice"]//text()[contains(., "$")]').extract()
        if not price:
            price = response.xpath('//h1[@class="product-price"]/span[not(@class)]/text()').extract()
        loader.add_value('price', price[0])
        loader.add_value('url', response.url)
        loader.add_xpath('name', "//h1[@class='product-name']//text()")
        product_name = ''.join(response.xpath("//h1[@class='product-name']//text()").extract())
        loader.add_value('identifier', hashlib.md5(product_name.encode('utf-8')).hexdigest())
        loader.add_value('stock', '1')
        loader.add_value('category', response.meta['category'])
        brand = response.xpath("//tr[contains(., 'Brand')]/td[2]/text()").extract()
        brand = brand[-1] if brand else ''
        loader.add_value('brand', brand)
        loader.add_xpath('shipping_cost', "//div[contains(@class, 'listarrow') and contains(., 'Shipping')]/span/text()")
        sku = response.xpath('//span[@class="code"]/text()').re('Code: (.*)')
        sku = sku[-1].strip() if sku else ''
        loader.add_value('sku', sku)
        loader.add_xpath('image_url', "//meta[@property='og:image']/@content")
        yield loader.load_item()
