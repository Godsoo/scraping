# -*- coding: utf-8 -*-
import re

from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from product_spiders.utils import extract_price_eu


class PixmaniaSpider(BaseSpider):
    name = 'pixmania.com'
    allowed_domains = ['pixmania.fr']
    start_urls = ('http://www.pixmania.fr/',)

    def __init__(self, *args, **kwargs):
        super(PixmaniaSpider, self).__init__(*args, **kwargs)

        self.identifier_names = {}

        self.URLS = {
            'http://www.pixmania.fr/jardin-44-c.html': 'Jardin',
            'http://www.pixmania.fr/bricolage-115-c.html': 'Bricolage',
            'http://www.pixmania.fr/petit-electromenager/aspirateur-et-nettoyeur-443-m.html': 'Aspirateur et nettoyeur',
            'http://www.pixmania.fr/jardin/arrosage-2043-m.html': 'Arrosage',
            'http://www.pixmania.fr/jardin/outillage-a-main-2042-m.html': 'Outillage à main',
            'http://www.pixmania.fr/jardin/outillage-motorise-2041-m.html': 'Outillage motorisé'
        }

    def start_requests(self):
        for url, category in self.URLS.items():
            yield Request(url,
                          meta={'category': category})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        filters = hxs.select('//aside[@id="filters"]//li/a/@href').extract()

        for url in filters:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta, callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//form//div[contains(@class, "resultList")]/article'
                              '//*[contains(@class, "productTitle")]/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          callback=self.parse_product,
                          meta=response.meta)

        pages = hxs.select('//ul[@class="pagination"]//a/@href').extract()

        for url in pages:
            yield Request(urljoin_rfc(base_url, url), meta=response.meta, callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta

        products = hxs.select('//form//div[contains(@class, "resultList")]/article'
                              '//*[contains(@class, "productTitle")]/a/@href').extract()
        if products:
            return
            # for x in self.parse(response):
                # yield x
            # return

        base_url = get_base_url(response)
        category = response.meta.get('category', '')
        try:
            category = category.encode(response.encoding)
        except:
            category = category.decode(response.encoding)
        price = hxs.select('//div[contains(@class,"productDetail")]//ins[@itemprop="price"]/@content').extract()
        if not price:
            price = "0.0"
        else:
            price = price[0]

        identifier = response.url.split('/')[-1].split('-')[0]

        try:
            main_name = hxs.select('//span[@itemprop="name"]/text()').extract()[0].strip()
        except:
            main_name = ''
        try:
            brand = hxs.select('//span[@itemprop="brand"]/text()').extract()[0].strip()
        except:
            brand = ''

        product_name = brand + ' ' + main_name
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()

        meta['name'] = product_name
        meta['url'] = response.url
        meta['brand'] = brand
        meta['price'] = price
        meta['image_url'] = image_url
        meta['sku'] = identifier
        meta['identifier'] = identifier
        meta['category'] = category

        sellers_url = hxs.select('//a[contains(@href, "all_seller")]/@href').extract()
        if sellers_url:
            yield Request(sellers_url[0].strip(), callback=self.parse_sellers, meta=meta)
            return

        # stock = hxs.select('//div[contains(@class, "availability")]/div/strong[contains(@class, "available")]/i[@class="icon-ok"]')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('brand', brand)
        loader.add_value('price', self._encode_price(price))
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('image_url', image_url)
        loader.add_value('category', category)
        # if not stock:
        #     loader.add_value('stock', 0)
        # else:
        loader.add_value('stock', 1)

        product = loader.load_item()
        self.set_identifier_name(product)
        yield product

    def parse_sellers(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        sellers = hxs.select('//div[@class="merchant product"]')
        for seller in sellers:
            price = seller.select('.//span[@class="currentPrice"]/ins/text()').extract()[0]
            seller_name = seller.select('.//p[@class="soldby"]//strong//text()').extract()
            # stock = seller.select('.//p[@class="availability"]/span[contains(@class, "available")]/i[@class="icon-ok"]')
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', meta['identifier'] + '-' + seller_name[0])
            loader.add_value('name', meta['brand'] + ' ' + meta['name'])
            loader.add_value('category', meta['category'])
            loader.add_value('brand', meta['brand'])
            loader.add_value('sku', meta['sku'])
            loader.add_value('url', meta['url'])
            loader.add_value('price', self._encode_price(price))
            loader.add_value('image_url', meta['image_url'])
            loader.add_value('dealer', 'Pix - ' + seller_name[0] if seller_name else 'Pixmania.com')
            loader.add_value('stock', 1)

            product = loader.load_item()
            self.set_identifier_name(product)
            yield product
        if not sellers:
            self.errors.append('WARNING: no sellers in %s' % response.url)

    def _encode_price(self, price):
        return price.replace(',', '.').encode("ascii", "ignore")

    def set_identifier_name(self, product):
        if product['identifier'] in self.identifier_names:
            product['name'] = self.identifier_names[product['identifier']]
        else:
            self.identifier_names[product['identifier']] = product['name']

    """
    Overwrites BSM method
    """
    def closing_parse_simple(self, *args, **kwargs):
        for product in super(PixmaniaSpider, self).closing_parse_simple(*args, **kwargs):
            self.set_identifier_name(product)
            yield product
