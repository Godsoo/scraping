# -*- coding: utf-8 -*-

import datetime
import os
import csv
import re

from scrapy import Spider, Request
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.utils import extract_price_eu
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)
from sonaeitems import SonaeMeta


HERE = os.path.dirname(os.path.abspath(__file__))


class PCDigaSpider(Spider):
    name = 'sonae-pcdiga.com'
    allowed_domains = ['pcdiga.com']
    start_urls = ['https://www.pcdiga.com/?stock_loja=0']

    user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:40.0) Gecko/20100101 Firefox/40.0'

    all_products_filename = os.path.join(HERE, 'pcdiga_all_products.csv')

    def start_requests(self):
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        self.all_products_collected = False
        self.collected_ids = set()
        self.products_meta = {}
        with open(self.all_products_filename) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.products_meta[row['identifier']] = row

        yield Request('https://www.pcdiga.com/pcdiga-promocoes',
                      meta={'promo': True},
                      callback=self.parse_products)

    def spider_idle(self, spider):
        if not self.all_products_collected:
            self.all_products_collected = True
            self.parse_deletions = True  # Set parse_deletions to True
            self.log('Spider idle parsing homepage')
            for url in self.start_urls:
                req = Request('https://www.pcdiga.com/marcas', callback=self.parse_brands)
                self._crawler.engine.crawl(req, self)
        elif self.parse_deletions:
            self.parse_deletions = False
            for url in self.deletion_urls():
                req = Request(url, callback=self.parse_product)
                self._crawler.engine.crawl(req, self)

    def spider_closed(self, spider):
        fieldnames = ['identifier', 'sku', 'category', 'brand', 'name', 'url', 'price', 'promo_start', 'promo_end']
        with open(self.all_products_filename, 'w') as f:
            writer = csv.DictWriter(f, fieldnames)
            writer.writeheader()
            for row in self.products_meta.values():
                writer.writerow(row)

    def deletion_urls(self):
        for id_, data in self.products_meta.iteritems():
            if id_ not in self.collected_ids:
                yield data['url']

    def parse_brands(self, response):
        brands = response.xpath('//div[@class="brands"]//a/@href').extract()
        for url in brands:
            yield Request(response.urljoin(url), callback=self.parse_products)

    def parse_products(self, response):
        next_page = response.xpath('//div[@class="pages"]//a[@class="next"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]), meta=response.meta, callback=self.parse_products)

        products = response.xpath('//ul[contains(@class, "products-grid")]/li[contains(@class, "item")]')
        for product_xs in products:
            name = product_xs.xpath('div[@class="product-info"]/h2[@class="product-name"]/a/text()').extract()[0]
            url = product_xs.xpath('div[@class="product-info"]/h2[@class="product-name"]/a/@href').extract()[0]
            identifier = product_xs.xpath('div[@class="product-info"]/div[@class="actions"]//*[contains(@id, "product-price-")]/@id').re(r'(\d+)')[0]
            price = ''.join(product_xs.xpath('div[@class="product-info"]/div[@class="actions"]//*[contains(@id, "product-price-")]/span/text()').re(r'[\d\.,]+'))
            brand = product_xs.xpath('div[@class="product-info"]/p[@class="product-brand"]/img/@title').extract()
            image_url = product_xs.xpath('.//img[contains(@id, "product-collection-image-")]/@src').extract()
            out_stock = bool(product_xs.xpath('.//i[contains(@class, "icon-stock-outs")]').extract())
            try:
                sku = product_xs.xpath('div[@class="product-info"]/div[@class="product-sku"]/text()').extract()[0].strip()
            except:
                sku = '0'

            l = ProductLoader(item=Product(), response=response)
            if image_url:
                l.add_value('image_url', response.urljoin(image_url[0]))
            l.add_value('url', url)
            l.add_value('name', name)
            l.add_value('identifier', identifier)
            l.add_value('price', extract_price_eu(price))
            l.add_value('brand', brand)
            if sku != '0':
                l.add_value('sku', sku)
            if out_stock:
                l.add_value('stock', 0)

            product = l.load_item()

            product['metadata'] = SonaeMeta()

            if identifier in self.products_meta:
                prev_meta = self.products_meta[identifier]
                if prev_meta['sku']:
                    product['sku'] = prev_meta['sku']
                product['category'] = prev_meta['category']
            else:
                prev_meta = {}
            promo = response.meta.get('promo', False)
            promo_start = prev_meta.get('promo_start')
            promo_end = prev_meta.get('promo_end')
            today = datetime.datetime.now().strftime('%Y-%m-%d')

            product['metadata']['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            if promo:
                product['metadata']['promo_start'] = promo_start if promo_start and not promo_end else today
                product['metadata']['promo_end'] = ''
            elif promo_start:
                product['metadata']['promo_start'] = promo_start
                product['metadata']['promo_end'] = today if not promo_end else promo_end

            self._update_product_meta(product)
            self.collected_ids.add(product['identifier'])

            yield product

    def parse_product(self, response):
        name = response.xpath('//div[@class="product-name"]/h1/text()').extract()[0]
        url = response.url
        identifier = re.findall(r'/id/(\d+)', response.url)[0]
        price = ''.join(re.findall(r'[\d\.,]+',
                                   response.xpath('//div[@class="product-essential"]//div[contains(@class, '
                                                  '"add-to-cart-wrapper")]//*[contains(@id, "product-price-")]/span/text()')
                                   .extract()[0]))
        brand = response.xpath('.//div[@class="product-brand"]//img/@title').extract()
        image_url = response.xpath('//img[@id="image-main"]/@src').extract()
        out_stock = bool(response.xpath('.//span[@class="shipping-run"]/i[contains(@class, "icon-stock-outs")]').extract())
        try:
            sku = response.xpath('//div[@class="product-sku"]//text()').extract()[0].strip()
        except:
            sku = ''

        l = ProductLoader(item=Product(), response=response)
        if image_url:
            l.add_value('image_url', response.urljoin(image_url[0]))
        l.add_value('url', url)
        l.add_value('name', name)
        l.add_value('identifier', identifier)
        l.add_value('price', extract_price_eu(price))
        l.add_value('brand', brand)
        if sku:
            l.add_value('sku', sku)
        if out_stock:
            l.add_value('stock', 0)

        product = l.load_item()

        product['metadata'] = SonaeMeta()

        if identifier in self.products_meta:
            prev_meta = self.products_meta[identifier]
            if prev_meta['sku']:
                product['sku'] = prev_meta['sku']
            product['category'] = prev_meta['category']
        else:
            prev_meta = {}
        promo = response.meta.get('promo', False)
        promo_start = prev_meta.get('promo_start')
        promo_end = prev_meta.get('promo_end')
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        product['metadata']['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if promo:
            product['metadata']['promo_start'] = promo_start if promo_start and not promo_end else today
            product['metadata']['promo_end'] = ''
        elif promo_start:
            product['metadata']['promo_start'] = promo_start
            product['metadata']['promo_end'] = today if not promo_end else promo_end

        self._update_product_meta(product)
        self.collected_ids.add(product['identifier'])

        yield product

    def _update_product_meta(self, product):
        self.products_meta[product['identifier']] = {
            'identifier': product['identifier'],
            'sku': product.get('sku', ''),
            'category': product.get('category', ''),
            'brand': product.get('brand', ''),
            'name': product['name'],
            'url': product['url'],
            'price': product['price'],
            'promo_start': product['metadata'].get('promo_start', ''),
            'promo_end': product['metadata'].get('promo_end', ''),
        }
