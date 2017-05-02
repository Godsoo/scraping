# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from decimal import Decimal
import re
import json
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider


class VintageKingSpider(BaseSpider):
    name = u'vintageking.com'
    allowed_domains = ['vintageking.com']
    start_urls = [
        u'http://www.vintageking.com',
    ]
    # download_delay = 1

    def __init__(self, *args, **kwargs):
        super(VintageKingSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.process_subcategories, signals.spider_idle)

        self.subcategories = []
        self.exchange_rate = 0

    def process_subcategories(self, spider):
        if spider.name == self.name:
            self.log("Spider idle. Processing subcategories")
            url = None
            if self.subcategories:
                url = self.subcategories.pop(0)
            if url:
                r = Request(url, callback=self.parse)
                self._crawler.engine.crawl(r, self)
                raise DontCloseSpider

    def start_requests(self):
        yield Request('http://www.xe.com/currencyconverter/convert/?Amount=1&From=USD&To=GBP',
                      callback=self.parse_exchange_rate)

    def parse_exchange_rate(self, response):
        hxs = HtmlXPathSelector(response)
        self.exchange_rate = Decimal(response.css('span.uccResultAmount::text').extract_first())
        yield Request('http://vintageking.com', callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # categories
        urls = hxs.select('//ul[@id="nav"]//a/@href').extract()
        for url in urls:
            url = urljoin_rfc(base_url, url)
            if url not in self.subcategories:
                self.subcategories.append(url)

        category = hxs.select('//div[contains(@class, "breadcrumbs")]//a/text()').extract()
        if len(category) > 1:
            products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
            for url in products:
                yield Request(urljoin_rfc(base_url, url),
                              callback=self.parse_product,
                              meta={'category': category[1]})

        pages = hxs.select('//div[@class="pages"]//li/a/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product_name = hxs.select('//h1[@itemprop="name itemreviewed"]/text()').extract()
        if not product_name:
            return
        product_name = product_name[0].strip()
        image_url = hxs.select('//div[@class="product_main"]//img[@itemprop="image photo"]/@src').extract()
        if not image_url:
            image_url = hxs.select('//img[@itemprop="image photo"]/@src').extract()
        brand = hxs.select('//a[@class="brand-link"]/img/@title').extract()
        sku = hxs.select('//p[@itemprop="identifier"]/@content').extract()[0]
        sku = sku.replace('sku:', '')
        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
            for identifier, option_name in products.iteritems():
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', identifier)
                loader.add_value('name', product_data['childProducts'][identifier]['productName'])
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                price = extract_price(product_data['childProducts'][identifier]['price'])
                price = price * self.exchange_rate * Decimal(1.2) + 100
                loader.add_value('price', price)
                loader.add_value('url', response.url)
                loader.add_value('category', response.meta.get('category', ''))
                if brand:
                    loader.add_value('brand', brand[0])
                loader.add_value('sku', sku)
                yield loader.load_item()
        else:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', response.url)
            loader.add_value('name', product_name)
            if brand:
                loader.add_value('brand', brand[0])
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//div[@class="price-box"]//span[@class="price"]/text()').extract()
            if price:
                price = extract_price(price[0].replace(',', ''))
                price = price * self.exchange_rate * Decimal(1.2) + 100
            else:
                price = 0
            loader.add_value('price', price)
            loader.add_value('category', response.meta.get('category', ''))
            loader.add_value('sku', sku)
            identifier = hxs.select('//div[@class="no-display"]//input[@name="product"]/@value').extract()[0]
            loader.add_value('identifier', identifier)
            yield loader.load_item()
