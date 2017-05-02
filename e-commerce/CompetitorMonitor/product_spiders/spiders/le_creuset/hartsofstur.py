import re
import os
import time
import hashlib
import csv
import itertools
import json
import copy
from urlparse import urljoin
from urllib import urlencode
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log
from scrapy.shell import inspect_response

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price

HERE = os.path.abspath(os.path.dirname(__file__))

class HartsOfSturSpider(BaseSpider):
    name = 'lecreuset-hartsofstur.com'
    #download_delay = 3
    seen_ids = []
    allowed_domains = ['hartsofstur.com']
    start_urls = ['http://www.hartsofstur.com/acatalog/Le_Creuset_Cookware.html']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        categories = hxs.select('//a[@class="more"]/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        next_page = False # hxs.select().extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        for url in hxs.select('//a[@class="button" and contains(text(),"Product")]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        log.msg(response.url)
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        identifier = response.url.split('/')[-1].split('-')[-1].split('.')[0]
        log.msg('Identifier: %s' % identifier)
        log.msg(repr(self.seen_ids))
        if identifier in self.seen_ids:
            return
        else:
            self.seen_ids.append(identifier)
        loader.add_value('identifier', identifier)
        sku = hxs.select('//p[@class="pmeta"]/text()').re('(\d+)')
        loader.add_value('sku', sku)
        name = hxs.select('//div[@class="prod-box"]/h1//text()').extract()
        extra_data = name[1].strip() if len(name) > 1 else ''
        loader.add_value('name', name[0])
        #price
        price = re.sub('[\r\n\t]+', ' ', hxs.select('//h5[@class="product-price"]//div[contains(@id,"StaticPrice")]/span/text()[normalize-space()]')[0].extract())
        loader.add_value('price', price)
        #image_url
        image_url = hxs.select('//img[@class="product-image"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        #brand
        loader.add_value('brand', 'Le Creuset')
        #category
        category = hxs.select('//ul[@class="breadcrumbs"]')[0].select('.//a/text()').extract()
        loader.add_value('category', ' > '.join(category[2:]))
        #shipping_cost
        price = Decimal(loader.get_output_value('price'))
        if price < 20.00:
            loader.add_value('shipping_cost', '2.00')
        elif 20.00 <= price < 40.00:
            loader.add_value('shipping_cost', '4.99')

        product = loader.load_item()

        options = hxs.select('.//select/option[contains(@class,"%s")]' % identifier)
        if options:
            sid = hxs.select('//input[@type="hidden" and @name="SID"]/@value')[0].extract()
            stock_url = 'http://www.hartsofstur.com/cgi-bin/st000001.pl?ACTION=GETSTOCK&REF=%(identifier)s&SID=%(sid)s&timestamp=%(timestamp)s'
            items = []
            for option in options:
                item = copy.deepcopy(product)
                option_name = option.select('./text()')[0].extract().strip()
                option_identifier = option.select('./@class').re('_(\d+)_')[0]
                self.seen_ids.append(option_identifier)
                item['identifier'] = "%s_%s" % (identifier, option_identifier.strip())
                item['name'] += ' %s %s' % (option_name, extra_data)
                item['name'] = item['name'].strip()
                items.append(item)
            yield Request(stock_url % {'identifier': identifier, 'sid': sid, 'timestamp': int(time.time())}, meta={'items': items}, callback=self.parse_stock)
        else:
            product['name'] += ' %s' % extra_data
            yield product

    def parse_stock(self, response):
        items = response.meta.get('items')
        stock = json.loads(response.body)
        for item in items:
            if stock.get(item['identifier']) and stock.get(item['identifier']) == 0:
                item['stock'] = 0
            yield item