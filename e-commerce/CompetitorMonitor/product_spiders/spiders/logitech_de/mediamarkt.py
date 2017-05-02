import os
import re
import json
import csv
import itertools
import urlparse

from copy import deepcopy

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import (
    Product,
    ProductLoaderEU as ProductLoader
)

HERE = os.path.abspath(os.path.dirname(__file__))

class MediamarktSpider(BaseSpider):
    name = 'logitech_german-mediamarkt.com'
    allowed_domains = ['mediamarkt.de']

    start_urls = ('http://www.mediamarkt.de/webapp/wcs/stores/servlet/MultiChannelSearch?storeId=48353&langId=-3&searchProfile=onlineshop&searchParams=%2FSearch.ff%3Fquery%3D%2A%26filterbrand%3DLOGITECH%26channel%3Dmmdede&query=LOGITECH&sort=name',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('identifier', 'mpn'), ('identifier', 'ean13')]

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Mediamarkt'] != 'No Match':
                    yield Request(row['Mediamarkt'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//li[@class="pagination-next"]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]) + '&sort=name')

        products = hxs.select('//div[@class="content "]/h2/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        retries = response.meta.get('retries', 0)
        if retries < 5:
            yield Request(response.url, meta={'retries': retries + 1}, dont_filter=True)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        meta = response.meta

        loader = ProductLoader(response=response, item=Product())

        category = hxs.select('//ul[@class="breadcrumbs"]/li/a/text()').extract()

        identifier = re.search('\'ean\',\'(.*?)\'', response.body).group(1)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('identifier', identifier)
        name = hxs.select('//h1[@class="detail__title"]/text()').extract()
        if not name:
            name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        loader.add_value('name', name[0].strip())
        price = hxs.select('//img[@class="buybox__pricetag"]/@alt|//*[@itemprop="price"]/text()').extract()
        if price:
            price = price[0]
        else:
            price = '0'
        sku = meta.get('sku')
        if sku:
            loader.add_value('sku', meta['sku'])
            loader.add_value('brand', meta['brand'])
        else:
            loader.add_value('brand', 'Logitech')

        if category:
            loader.add_value('category', category[-1])
        shipping_cost = hxs.select('//*[@itemprop="price"]/following-sibling::small/text()').re(u'\xa0(.*)')
        if shipping_cost:
            loader.add_value('shipping_cost', shipping_cost[0].strip().replace(',', '.'))
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('image_url', '//div[contains(@class, "product-images")]/img/@src|//img[@itemprop="image"]/@src',
                         lambda imgs: urljoin_rfc(base_url, imgs[0]))
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)
        yield loader.load_item()

