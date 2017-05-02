# -*- coding: utf-8 -*-


"""
Account: Guitar Guitar
Name: guitar_guitar-andertons.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4600
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


import re
from scrapy import Spider, Request, FormRequest
from scrapy.spiders import SitemapSpider
from product_spiders.items import (
    ProductLoaderWithoutSpaces as ProductLoader,
    Product,
)
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from w3lib.url import add_or_replace_parameter

from product_spiders.base_spiders.primary_spider import PrimarySpider


class GuitarGuitarAndertons(SitemapSpider, PrimarySpider):
    name = 'guitar_guitar-andertons.co.uk'
    allowed_domains = ['andertons.co.uk']

    start_urls = ['https://www.andertons.co.uk/all-brands']
    sitemap_urls = ['https://www.andertons.co.uk/sitemap']
    sitemap_rules = [('/bc/', 'parse_category'), ('/p/', 'parse_product')]

    AJAX_URL = 'http://www.andertons.co.uk/ajax/easearch.asp'

    csv_file = 'andertons.co.uk_products.csv'
        
    def __init__(self, *args, **kwargs):
        super(GuitarGuitarAndertons, self).__init__(*args, **kwargs)
        self._all_categories_parsed = False
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        self.seen = set()

    def spider_idle(self, *args, **kwargs):
        return
        if not self._all_categories_parsed:
            self._all_categories_parsed = True
            req = Request('http://www.andertons.co.uk/',
                          dont_filter=True,
                          callback=self.parse_categories)
            self.crawler.engine.crawl(req, self)

    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.css('span#thisstkcode::text').extract_first()
        if not identifier:
            retries = response.meta.get('retries', 0)
            if retries > 9:
                self.logger.warning('No identifier found on %s' %response.url)
            else:
                self.logger.debug('Retry %s to get identifier' %response.url)
            meta = response.meta
            meta['retries'] = retries + 1
            yield response.request.replace('dont_filter=True', meta=meta)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/text()')
        price = response.css('span.prodPrice').xpath('.//span[@itemprop="price"]/text()').extract_first()
        loader.add_value('price', price)
        category = response.css('.breadcrumbs span::text').extract()[1:]
        loader.add_value('category', category)
        loader.add_css('image_url', '.main-product-photo::attr(href)')
        loader.add_css('brand', 'span#thisbrand::text')
        loader.add_css('stock', 'input#data-stock-qty::attr(value)')       
        yield loader.load_item()

    def _parse(self, response):
        yield Request('https://www.andertons.co.uk/b/268/ibanez',
                      self.parse_brand,
                      meta={'brand':'Ibanez', 'object_id': 268, 'page': 1})
        return
        brands = response.css('.brand-block')

        for brand_xs in brands:
            brand_name = ''.join(brand_xs.xpath('.//text()').extract()).strip()
            brand_url = response.urljoin(brand_xs.xpath('./a/@href').extract()[0])
            object_id = re.findall(r'/b/(\d+)/', brand_url)[0]
            page = 1
            yield Request(brand_url,
                              callback=self.parse_brand,
                              meta={'brand': brand_name,
                                    'object_id': object_id,
                                    'page': page})

    def parse_categories(self, response):
        categories = response.xpath('//*[@id="Nav1"]//a')
        for category_xs in categories:
            category_name = category_xs.xpath('text()').extract()[0].strip()
            category_url = category_xs.xpath('@href').extract()[0]
            category_url = response.urljoin(category_url)
            try:
                object_id = re.findall(r'/c/(\d+)', category_url)[0]
            except:
                continue
            page = 1
            yield FormRequest(category_url,
                              callback=self.parse_category,
                              meta={'category': category_name,
                                    'object_id': object_id,
                                    'page': page},
                              dont_filter=True)

    def parse_brand(self, response):
        products = response.css('div.product')
        for product_xs in products:
            product_name = product_xs.xpath('./a/@title').extract()[0]
            product_url = response.urljoin(product_xs.xpath('./a/@href').extract()[0])
            product_identifier = re.findall(r'/p/(.+?)/', product_url)[0]
            product_price = product_xs.xpath('.//span[@itemprop="price"]/text()').re(r'[\d\,.]+')[0]
            product_stock = product_xs.css('div.stockinfo::text').re(r'[\d\,.]+')
            product_image = product_xs.xpath('.//img[@alt]/@src').extract()

            loader = ProductLoader(item=Product(), selector=product_xs)
            loader.add_value('identifier', product_identifier)
            loader.add_value('sku', product_identifier)
            loader.add_value('name', product_name)
            loader.add_value('url', product_url)
            loader.add_value('price', product_price)
            if product_stock:
                loader.add_value('stock', int(product_stock[0]))
            if product_image:
                loader.add_value('image_url', response.urljoin(product_image[0]))
            loader.add_value('brand', response.meta['brand'])
            loader.add_value('category', response.meta['brand'])

            yield loader.load_item()

        pages = set(response.xpath('//ul[@id="pagelist1"]/li/a/text()').extract())
        next_page = response.meta['page'] + 1
        if str(next_page) in pages:
            url = add_or_replace_parameter(response.url, 'p', next_page)
            url = add_or_replace_parameter(url, 'q', response.meta['object_id'])
            yield Request(url,
                              callback=self.parse_brand,
                              meta={'brand': response.meta['brand'],
                                    'object_id': response.meta['object_id'],
                                    'page': next_page})

    def parse_category(self, response):
        products = response.css('div.product')    
        for product_xs in products:
            try:
                product_name = product_xs.xpath('./a/@title').extract()[0]
            except IndexError:
                continue
            product_url = response.urljoin(product_xs.xpath('./a/@href').extract()[0])
            if product_url not in self.seen:
                yield Request(product_url, self.parse_product, dont_filter=True)
                self.seen.add(product_url)
            continue
            product_identifier = re.findall(r'/p/(.+?)/', product_url)[0]
            product_price = product_xs.xpath('.//span[@itemprop="price"]/text()').re(r'[\d\,.]+')[0]
            product_stock = product_xs.css('div.stockinfo::text').re(r'[\d\,.]+')
            product_image = product_xs.xpath('.//img[@alt]/@src').extract()

            loader = ProductLoader(item=Product(), selector=product_xs)
            loader.add_value('identifier', product_identifier)
            loader.add_value('sku', product_identifier)
            loader.add_value('name', product_name)
            loader.add_value('url', product_url)
            loader.add_value('price', product_price)
            if product_stock:
                loader.add_value('stock', int(product_stock[0]))
            if product_image:
                loader.add_value('image_url', response.urljoin(product_image[0]))
            loader.add_value('category', response.meta['category'])

            yield loader.load_item()
        return
    
        pages = set(response.xpath('//ul[@id="pagelist1"]/li/a/text()').extract())
        next_page = response.meta['page'] + 1
        if str(next_page) in pages:
            url = add_or_replace_parameter(response.url, 'p', next_page)
            url = add_or_replace_parameter(url, 'q', response.meta['object_id'])
            yield Request(url,
                              callback=self.parse_category,
                              meta={'category': response.meta['category'],
                                    'object_id': response.meta['object_id'],
                                    'page': next_page})
