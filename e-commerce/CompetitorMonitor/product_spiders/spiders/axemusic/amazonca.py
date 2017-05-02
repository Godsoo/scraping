import re
import os
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse, TextResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib
from decimal import Decimal

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.spiders.BeautifulSoup import BeautifulSoup
from scrapy import log
from pricecheck import valid_price

HERE = os.path.abspath(os.path.dirname(__file__))

class AmazonSpider(BaseSpider):
    name = 'axemusic-amazon.ca'
    allowed_domains = [u'amazon.ca', u'www.amazon.ca']
    start_urls = (u'http://www.amazon.ca', )

    def __init__(self, *args, **kwargs):
        super(AmazonSpider, self).__init__(*args, **kwargs)
        self.search_urls = u'http://www.amazon.ca/s/ref=nb_sb_noss?url=search-alias%%3Daps&field-keywords=%(q)s'

    def start_requests(self):
        with open(os.path.join(HERE, 'amazon_skus.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['sku']
                url = self.search_urls
                yield Request(url % {'q': row['name'].replace(u' ', u'+').replace(u'&', u' ')}, meta={'sku': sku, 'price': row['price']}, dont_filter=True)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        soup = BeautifulSoup(response.body)
        products = soup.find('div', id='atfResults')
        if products:
            products = products.findAll('div', id=re.compile('result_\d+$'))
            url = products[0].find('a')['href']
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', u'//span[@id="btAsinTitle"]/text()')
        loader.add_value('url', response.url)

        loader.add_xpath('image_url', u'//tr[@id="prodImageContainer"]//img/@src')
        if not loader.get_output_value(u'image_url'):
            soup = BeautifulSoup(response.body)
            image_url = soup.find(lambda tag: tag.name == u'img' and tag.findParent(u'tr', id=u'prodImageContainer'))
            if image_url:
                loader.add_value('image_url', image_url.get(u'src'))

        loader.add_xpath('brand', u'//span[@class="tsLabel" and contains(text(),"Brand")]/following-sibling::span/text()')

        loader.add_xpath('price', u'//b[@class="priceLarge"]/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', u'//span[@class="priceLarge"]/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', u'//span[@class="price"]/text()')

        loader.add_value('sku', response.meta['sku'])
        loader.add_value('identifier', response.meta['sku'].lower())
        yield loader.load_item()

    def match_skus(self, sku1, sku2):
        sku1 = sku1.replace(u'-', u'').replace(u' ', u'').lower()
        sku2 = sku2.replace(u'-', u'').replace(u' ', u'').lower()
        return sku1 == sku2 or sku1.startswith(sku2) or sku1.endswith(sku2)
