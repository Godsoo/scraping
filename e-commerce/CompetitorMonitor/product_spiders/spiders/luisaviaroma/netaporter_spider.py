import os
import csv
import re

import shutil

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))

class NetAPorterSpider(BaseSpider):
    name = 'net-a-porter.com'
    allowed_domains = ['net-a-porter.com', 'xe.com']
    start_urls = ('http://www.net-a-porter.com',)

    categories = ['http://www.net-a-porter.com/Shop/Designers/Giuseppe_Zanotti']

    products_file = os.path.join(HERE, 'netaporter_products.csv')

    def __init__(self, *args, **kwargs):
        super(NetAPorterSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.exchange_rate = 1

    def spider_closed(self, spider):
        """
        On full run saves crawl results for future use if it's full run then.
        """
        self.log("Saving crawl results")
        shutil.copy('data/%s_products.csv' % spider.crawl_id, self.products_file)

    def start_requests(self):
        params = {'channel': 'INTL',
                  'country': 'AE',
                  'httpsRedirect': '',
                  'language': 'en',
                  'redirect': ''}

        req = FormRequest(url="http://www.net-a-porter.com/intl/changecountry.nap?overlay=true", formdata=params,
                          callback=self.parse_exchange_rate)
        yield req

    def parse_exchange_rate(self, response):
        yield Request('http://www.xe.com/currencyconverter/convert/?Amount=1&From=GBP&To=EUR', callback=self.parse)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        exchange_rate = hxs.select('//tr[@class="uccRes"]/td[last()]/text()').re('[\d\.]+')[0]

        self.exchange_rate = extract_price(exchange_rate)

        with open(os.path.join(HERE, 'luisaviaroma.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Net-a-Porter'] != 'NO MATCHES':
                    meta = {
                        'category': row['Category'],
                        'brand': row['Brand'],
                        'sku': row['Codes'],
                        'url': row['Net-a-Porter']
                    }
                    yield Request(row['Net-a-Porter'], callback=self.parse_product, meta=meta)

        if os.path.exists(self.products_file) and os.path.isfile(self.products_file):
            with open(self.products_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    meta = {
                        'category': row['category'],
                        'brand': row['brand'],
                        'sku': row['sku'],
                        'url': row['url']
                    }
                    yield Request(row['url'], callback=self.parse_product, meta=meta)

        for category in self.categories:
            yield Request(category, callback=self.parse_category)

    def parse_category(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        products = hxs.select('//div[@class="description"]/a/@href').extract()
        for product in products:
            category = hxs.select('//div[@class="product-list-title"]/h1/a/text()').extract()[0]
            url = urljoin_rfc(base_url, product)
            meta['category'] = category
            yield Request(url, callback=self.parse_product, meta=meta)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        meta = response.meta

        l = ProductLoader(item=Product(), response=response)
        url = meta.get('url') if meta.get('url', None) else response.url
        l.add_value('url', url)

        identifier = filter(lambda d: d.strip() != '', hxs.select('//input[@id="productId"]/@value').extract())
        if not identifier:
            identifier = hxs.select('//*[@itemprop="sku"]/@content').extract()
        if not identifier:
            identifier = re.findall("product/([^/]*)/", url)

        if identifier:
            identifier = identifier[0]
        l.add_value('identifier', identifier)

        brand = hxs.select('//h2[@itemprop="brand"]/a/text()').extract()[0]
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        l.add_value('name', brand + ' ' + name)

        sku = meta.get('sku', None)
        if not sku:
            sku = hxs.select('//meta[@itemprop="sku"]/@content').extract()
            sku = sku[0] if sku else ''
        l.add_value('sku', sku)

        brand = meta.get('brand') if meta.get('brand', None) else brand
        l.add_value('brand', brand)

        image_url = hxs.select('//img[@id="medium-image"]/@src').extract()
        if image_url:
            l.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        l.add_value('category', meta.get('category'))
        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        if price:
            price = extract_price(price[0]) * self.exchange_rate
        else:
            price = 0
        l.add_value('price', price)
        yield l.load_item()
