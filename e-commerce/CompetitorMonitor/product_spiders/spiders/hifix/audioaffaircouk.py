import logging
import re
import os
import csv
import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))


class AudioaffairCoUkSpider(BaseSpider):
    name = 'audioaffair.co.uk'
    allowed_domains = ['audioaffair.co.uk']
    start_urls = ('http://www.audioaffair.co.uk/',
                  'http://www.audioaffair.co.uk/catalogsearch/result/?q=%25')
    ids = {}
    errors = []

    def __init__(self, *args, **kwargs):
        super(AudioaffairCoUkSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self._parsed_deletions = False
        self._urls = []
        self._all_products_csv = os.path.join(HERE, 'audioaffair_products.csv')

        if os.path.exists(self._all_products_csv):
            shutil.copy(self._all_products_csv, self._all_products_csv + '.bak')

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, self._all_products_csv)

    def spider_idle(self, spider):
        if not self._parsed_deletions:
            self._parsed_deletions = True
            self._crawler.engine.crawl(
                Request('http://www.audioaffair.co.uk/',
                        callback=self.parse_deletions,
                        dont_filter=True), self)

    def parse_deletions(self, response):
        if os.path.exists(self._all_products_csv):
            with open(self._all_products_csv) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row['url'] not in self._urls:
                        yield Request(row['url'], callback=self.parse_product)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # categories
        category_urls = hxs.select('//ul[@id="nav"]//li/a/@href').extract()
        for url in category_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        # pages
        pages_urls = hxs.select('//div[@class="pager"]//a/@href').extract()
        for url in pages_urls:
            url = urljoin_rfc(base_url, url)
            yield Request(url)

        # products list
        products = hxs.select("//li[contains(@class, 'item')]")
        if not products:
            logging.error("ERROR!! NO PRODUCTS!! %s " % response.url)
        for product_el in products:
            name = product_el.select('.//h2[@class="product-name"]/a/text()').extract()
            if not name:
                continue

            discountinued = product_el.select('div/div[@class="cant_buy_online"]/p/text()').extract()
            if discountinued:
                continue

            name = name[0]

            url = product_el.select('.//h2[@class="product-name"]/a/@href').extract()
            if not url:
                logging.error("ERROR!! NO URL!! %s %s" % (response.url, name))
                continue
            url = url[0]
            url = urljoin_rfc(base_url, url)

            price = product_el.select('.//span[@class="price"]/text()').extract()
            if not price:
                logging.error("ERROR!! NO PRICE!! %s %s" % (response.url, name))
                continue
            price = extract_price(price.pop())

            identifier = product_el.select(u'.//div[@class="buy-now"]/a').re(r'/product/(\d+)/form_key')
            if not identifier:
                identifier = product_el.select(u'.//span[contains(@id, "product-price")]/@id').re(r'product-price-(\d+)')

            if not identifier:
                continue
            identifier = identifier.pop()

            loader = ProductLoader(item=Product(), selector=product_el)
            loader.add_value('identifier', identifier)
            loader.add_value('url', url)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_xpath('image_url', u'.//a[contains(@class, "product-image")]//img/@src')
            item = loader.load_item()

            self._urls.append(item['url'])
            if identifier not in self.ids or price != self.ids[identifier]:
                self.ids[identifier] = price
                yield item

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        discontinued = hxs.select('//div[@class="cant_buy_online"]/p/text()').extract()
        if discontinued:
            return

        name = hxs.select('//*[@itemprop="name"]/text()').extract()
        if not name:
            name = hxs.select('//div[@class="product-name-main"]/h2/text()').extract() or hxs.select('//div[@class="product-name"]/text()').extract()
        price = hxs.select('//*[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//*[contains(@id, "product-price-")]/text()').extract()
        if not price:
            self.errors.append("No price on " + response.url)
        price = extract_price(price.pop())
        image_url = hxs.select('//*[@itemprop="image"]/@src').extract()
        if not image_url:
            image_url = hxs.select('//div[@class="main-image"]//img/@src').extract() or hxs.select('//div[contains(@class, "product-image")]//img/@src').extract()
        identifier = hxs.select('//input[@name="product"]/@value').extract().pop()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('price', price)

        if image_url:
            loader.add_value('image_url', image_url[0].replace('/60x/', '/300x/'))

        if identifier not in self.ids or price != self.ids[identifier]:
            self.ids[identifier] = price
            yield loader.load_item()
