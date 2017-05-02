# -*- coding: utf-8 -*-

import os
from decimal import Decimal
import pandas as pd
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import DATA_DIR


class ColyerSpider(BaseSpider):
    name = u'colyer.co.uk'
    allowed_domains = ['evl245.s1.e-storefront.co.uk']
    start_url1 = 'http://evl245.s1.e-storefront.co.uk/storefront/Products-Az'
    start_url2 = 'http://evl245.s1.e-storefront.co.uk/storefront/Home'

    def __init__(self, *args, **kwargs):
        super(ColyerSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.try_deletions = True
        self.new_ids = []

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def spider_idle(self, spider):
        if self.try_deletions:
            self.try_deletions = False

            filename = self._get_prev_crawl_filename()
            if filename and os.path.exists(filename):
                old_products = pd.read_csv(filename, dtype=pd.np.str)
                deletions = old_products[old_products.isin(self.new_ids) == False]
                for url in deletions['url']:
                    request = Request(url, dont_filter=True, callback=self.parse_product)
                    self._crawler.engine.crawl(request, self)

    def start_requests(self):
        yield Request(self.start_url2, callback=self.parse_categories)
        yield Request(self.start_url1, callback=self.parse_az)

    def parse_az(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//div[@class="brand-az"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories_az)

    def parse_categories_az(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//ul[@class="brands"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list_az)

    def parse_products_list_az(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//div[@class="list"]//p[@class="description"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        urls = hxs.select('//div[@class="pageNumbers"]//li//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list_az)

    def parse_categories(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//*[@id="column"]/div[3]/ul/li/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories_products)

    def parse_categories_products(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//h1[@class="cat"]/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories_products)
        if not urls:
            urls = hxs.select('//div[@class="list"]//p[@class="description"]/a/@href').extract()
            for url in urls:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
            urls = hxs.select('//div[@class="pageNumbers"]//li//a/@href').extract()
            for url in urls:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_categories_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        test = hxs.select('//*[@id="sitecontainer"]').extract()
        if not test:
            retry = int(response.meta.get('retry', 0))
            retry += 1
            if retry > 10:
                self.log('ERROR: giving up loading URL:{}'.format(response.url))
                return
            else:
                yield Request(response.url, meta={'retry': retry}, callback=self.parse_product)

        redirected_urls = response.meta.get('redirect_urls', None)
        if redirected_urls and 'ProductHelp-' in response.url:
            self.log('Skips product, redirected url: ' + str(redirected_urls[0]))
            return

        url = urljoin_rfc(base_url, response.url)
        image_url = hxs.select('//*[@id="sitecontainer"]//img[@class="main"]/@src').extract()
        product_name = hxs.select('//*[@id="sitecontainer"]//p[@class="description"]/text()').extract()[0].strip()
        overview = hxs.select('//*[@id="sitecontainer"]//ul[@class="overview"]//li/text()').extract()
        brand = ''
        for item in overview:
            if item.strip().startswith('Brand:'):
                brand = item.replace('Brand:', '').strip()
                break
        category = hxs.select('//*[@id="breadcrumb"]//li/text()').extract()
        category = category[0].strip() if category else ''

        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//*[@id="sitecontainer"]//form[@name="productAdd"]//input[@name="IdProduct"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        codes = hxs.select('//*[@id="sitecontainer"]//p[@class="code"]/strong/text()').extract()
        sku = ''
        for code in codes:
            if 'Manufacturer Ref:' in code:
                sku = code.replace('Manufacturer Ref:', '')
                break
            if 'Product code:' in code:
                sku = code.replace('Product code:', '')
        loader.add_value('sku', sku)
        loader.add_value('url', url)
        loader.add_value('name', product_name)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        price = hxs.select('//*[@id="sitecontainer"]//p[@class="inc"]/text()').extract()
        if price:
            price = extract_price(price[0].replace(u'\xa3', ''))
        else:
            price = hxs.select('//*[@id="sitecontainer"]//p[@class="exc"]/text()').extract()[0]
            price = extract_price(price.replace(u'\xa3', '')) * Decimal(1.2)
        loader.add_value('price', price)
        loader.add_value('brand', brand)
        loader.add_value('category', category)
        in_stock = hxs.select('//*[@id="sitecontainer"]//p[@class="stock"]/span/text()').re(r'(\d+)')
        if in_stock:
            loader.add_value('stock', in_stock[0])
        loader.add_value('shipping_cost', 5.95)

        product = loader.load_item()

        if product['identifier']:
            self.new_ids.append(product['identifier'])
            yield product
