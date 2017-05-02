'''
Spider for uk.farnell.com
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5507
'''

# -*- coding: utf-8 -*-

import os
import csv
import cStringIO
import shutil
from w3lib.url import url_query_cleaner, url_query_parameter
from decimal import Decimal
from urlparse import urljoin as urljoin_rfc
from scrapy.spider import Spider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


HERE = os.path.abspath(os.path.dirname(__file__))


class FarnellSpider(Spider):
    name = 'schneider_electric-uk_farnell_com'
    allowed_domains = ['uk.farnell.com']
    start_urls = ('http://uk.farnell.com/switches-relays/prl/results',
                  'http://uk.farnell.com/automation-process-control/prl/results')

    cache_data_file = os.path.join(HERE, 'farnell_cache.csv')

    def __init__(self, *args, **kwargs):
        super(FarnellSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        self.missing_urls = []

    def spider_idle(self, spider):
        if self.missing_urls:
            req = Request(self.start_urls[0],
                          dont_filter=True,
                          callback=self.get_missing_urls)
            self._crawler.engine.crawl(req, self)

    def get_missing_urls(self, response):
        while self.missing_urls:
            url = self.missing_urls.pop()
            yield Request(url, callback=self.parse_product)

    def start_requests(self):
        with open(os.path.join(HERE, 'products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request('http://uk.farnell.com/webapp/wcs/stores/servlet/Search?st=%s' % row['SKU Code'],
                              self.parse_search_results,
                              meta={'sku': row['SKU Code'].strip().upper()})
        return
    
        self.cache_data = {}
        if hasattr(self, 'prev_crawl_id'):
            shutil.copy('data/%s_products.csv' % self.prev_crawl_id, self.cache_data_file)
            with open(self.cache_data_file) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.cache_data[row['identifier']] = row
                    self.missing_urls.append(row['url'].decode('utf-8'))

        for url in self.start_urls:
            yield Request(url)

    def parse_search_results(self, response):
        products = response.xpath('//table[@id="sProdList"]/tbody/tr[td[@class="productImage"]]')
        for product in products:
            sku = product.css('p.wordBreak a::text').extract_first()
            if sku and sku.strip().upper() == response.meta['sku']:
                url = product.xpath('.//a[@class="sku"]/@href').extract_first().strip()
                url = url_query_cleaner(url)
                yield Request(url, self.parse_product)
                
        sku = response.xpath('//*[@itemprop="mpn"]/text()').extract_first()
        if not products and sku and sku.strip().upper() == response.meta['sku']:
            yield Request(url_query_cleaner(response.url),
                          self.parse_product,
                          dont_filter=True)
        
        urls = response.css('ul.categoryList a::attr(href)').extract()
        if not products and not sku and urls:
            for url in urls:
                yield Request(url, self.parse_search_results, meta=response.meta)
                    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        meta = response.meta.copy()
        categories_urls = response.xpath('//ul[@class="categoryList"]/li//a')
        for category in categories_urls:
            url = category.select('@href').extract()[0]
            name = category.select('text()').extract()[0].strip()
            if "/prl/results" not in url and 'webapp' not in url:
                url += "/prl/results"
            yield Request(urljoin_rfc(base_url, url), callback=self.parse, meta={'category': name})

        products = response.xpath('//table[@id="sProdList"]/tbody/tr[td[@class="productImage"]]')
        for product in products:
            try:
                identifier = product.select('.//a[@class="sku"]/text()').extract()[0].strip()
                stock = int(product.select('.//td[@class="availability"]/input[@class="hVal"]/@value').extract()[0])
                price = round(Decimal(product.css('.price input.hVal::attr(value)').extract()[0]), 2)
            except IndexError:
                continue
            if identifier in self.cache_data:
                product_cached = self.cache_data[identifier]
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('identifier', identifier)
                loader.add_value('name', product_cached['name'].decode('utf-8'))
                loader.add_value('url', product_cached['url'].decode('utf-8'))
                loader.add_value('sku', product_cached['sku'].decode('utf-8'))
                loader.add_value('category', product_cached['category'].decode('utf-8'))
                loader.add_value('image_url', product_cached['image_url'].decode('utf-8'))
                loader.add_value('brand', product_cached['brand'].decode('utf-8'))
                loader.add_value('price', price)
                loader.add_value('stock', stock)
                item = loader.load_item()

                try:
                    self.missing_urls.remove(item['url'])
                except ValueError:
                    pass

                yield item
            else:
                url = product.select('.//a[@class="sku"]/@href').extract()[0].strip()
                url = url_query_cleaner(url)
                if url in self.missing_urls:
                    self.missing_urls.remove(url)
                yield Request(url, callback=self.parse_product, meta=meta)

        pages = response.css('.pages .pageIt a::attr(href)').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse, meta=meta)

        if not products and not categories_urls:
            yield Request(url_query_cleaner(response.url), dont_filter=True, callback=self.parse_product, meta=meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brand = response.xpath('//span[@itemprop="http://schema.org/manufacturer"]/text()').extract_first() or response.xpath('//span[@itemprop="http://schema.org/brand"]/text()').extract_first()

        identifier = hxs.select('//input[@id="itemsArray"]/@value').extract()
        if not identifier:
            return
        sku = response.xpath('//*[@itemprop="mpn"]/text()').extract()[0].strip()
        product_loader = ProductLoader(item=Product(), selector=hxs)
        image_url = response.css('img#productMainImage::attr(src)').extract_first()
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url))

        category = response.meta.get('category', '')
        if not category:
            category = hxs.select('//div[@id="breadcrumb"]/ul/li/a/text()').extract()[-2].strip()

        product_loader.add_value('category', category)

        product_name = response.xpath('//div[@id="product"]//h1//text()').re('\S+')

        product_loader.add_value('name', product_name)
        product_loader.add_xpath('url', 'link[@rel="canonical"]/@href')
        product_loader.add_value('url', url_query_cleaner(response.url))
        product_loader.add_value('identifier', identifier.pop())

        product_loader.add_value('brand', brand)
        product_loader.add_value('sku', sku)
        price = ''.join(hxs.select('//table[contains(@class, "pricing")]//td[@class="threeColTd"][1]/text()').extract()).strip().split('(')[0].strip().replace(u'\xa3','')
        if price:
            price = extract_price(price)
            price = price.quantize(Decimal('.01'))
            product_loader.add_value('price', price)
        else:
            product_loader.add_value('price', 0)

        stock = response.css('span.availability::text').re('\d+')
        if stock:
            product_loader.add_value('stock', stock[0])
        else:
            product_loader.add_value('stock', 0)

        yield product_loader.load_item()
 
