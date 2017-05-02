import re
import os
import csv
import shutil

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader

import logging

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

HERE = os.path.abspath(os.path.dirname(__file__))


class PlayComSpider(BaseSpider):
    name = 'legouk-play.com'
    allowed_domains = ['www.rakuten.co.uk']
    start_urls = ['http://www.rakuten.co.uk/search/lego/931/',]

    _re_sku = re.compile('(\d\d\d\d\d?)')

    errors = []
    _urls = []

    def __init__(self, *args, **kwargs):
        super(PlayComSpider, self).__init__(*args, **kwargs)

        '''
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        
        if os.path.exists(os.path.join(HERE, 'play_products.csv')):
            shutil.copy(os.path.join(HERE, 'play_products.csv'),
                        os.path.join(HERE, 'play_products.csv.bak'))
        '''

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'play_products.csv'))

    def start_requests(self):

        '''
        if os.path.exists(os.path.join(HERE, 'play_products.csv')):
            with open(os.path.join(HERE, 'play_products.csv')) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['url'].strip() and row['url'] not in self._urls and row['url'].startswith('http'):
                        self._urls.append(row['url'])
                        self.log('>>> GET %s' % row['url'])
                        yield Request(row['url'], self.parse_product)
        '''

        for url in self.start_urls:
            self.log('>>> GET start url => %s' % url)
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # parse pages
        pages = hxs.select('//div[contains(@class, "b-pagination")]/ul/li/a/@href').extract()
        for next in pages:
            yield Request(urljoin_rfc(base_url, next))

        # parse products
        items = hxs.select('//li[@class="b-item"]/div/div[@class="b-img"]/div/a/@href').extract()
        for item in items:
            yield Request(urljoin_rfc(base_url, item), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sku = hxs.select('//span[@class="b-item"]').re("MPN: ([0-9]+)")
        identifier = hxs.select('//input[@name="item_id"]/@value').extract()[0]
        name = hxs.select('//h1[@class="b-ttl-main"]/text()').extract()[0]
        dealer_name = "".join(hxs.select('//h2[@id="auto_shop_info_name"]//text()').extract()).strip()
        price = hxs.select('//div[@class="b-product-main"]//meta[@itemprop="price"]/@content').extract()[0]
        brand = hxs.select('//div[contains(@class, "b-text-sub")]/text()').re("Manufacturer: ([a-zA-Z0-9]+)")
        categories = hxs.select('//ul[@class="b-breadcrumb"]/li/a/text()').extract()
        image_url = hxs.select('//div[contains(@class, "b-main-image")]/a/img/@data-frz-src').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        if sku:
            loader.add_value('sku', sku[0])
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('price', price)
        loader.add_value('dealer', dealer_name)
        if brand:
            loader.add_value('brand', brand[0])
        loader.add_value('category', categories)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        yield loader.load_item()
