# -*- coding: utf-8 -*-

import os
import re
import csv
import hashlib

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from product_spiders.utils import extract_price_eu
from product_spiders.config import DATA_DIR


HERE = os.path.abspath(os.path.dirname(__file__))


class MallSpider(BaseSpider):
    name = 'mall'
    allowed_domains = ['mall.pl']
    start_urls = ['https://www.mall.pl/site-map',
                  'https://www.mall.pl/kategoria',
                  'https://www.mall.pl/marek']

    def __init__(self, *args, **kwargs):
        super(MallSpider, self).__init__(*args, **kwargs)

        self.identifiers_viewed = []

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)

        if hasattr(self, 'prev_crawl_id'):
            prev_crawl_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            if os.path.exists(prev_crawl_filename):
                with open(prev_crawl_filename) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        yield Request(row['url'], callback=self.parse_product)

        yield Request('https://www.mall.pl/sitemap', callback=self.parse_sitemap)

    def parse_sitemap(self, response):
        products_sitemap = re.findall('<loc>(.*?/products/\d+)</loc>', response.body)
        for url in products_sitemap:
            yield Request(url, callback=self.parse_sitemap)

        if not products_sitemap:
            for url in re.findall('<loc>(.*)</loc>', response.body):
                yield Request(url, callback=self.parse_product)

    def parse(self, response):
        base_url = get_base_url(response)

        # we extract the categories urls
        categories = response.xpath('//*[@class="grid-cell"]//li/a/@href').extract()
        for category in categories:
            yield Request(
                urljoin_rfc(base_url, category).replace('//www.', '//m.'), # Use mobile version
                callback=self.parse_category
            )

    def parse_category(self, response):
        """
        While parsing a category page we need to look after a product or category list
        """
        base_url = get_base_url(response)

        # products
        product_urls = response.xpath('//*[contains(@class, "p-list")]/a/@href').extract()
        for product_url in product_urls:
            yield Request(
                urljoin_rfc(base_url.replace('//m.', '//www.'), product_url),
                callback=self.parse_product
            )

        # sub categories
        for category_url in response.xpath('//div[@class="guide"]//li/a/@href|//ul[@class="expand"]//li/a/@href|'
                                       '//nav[@class="nav-main"]//ul//li/a/@href').extract():
            yield Request(
                urljoin_rfc(base_url, category_url),
                callback=self.parse_category
            )

        # next page
        next_page_url_list = response.xpath('//div[@id="pagination"]//a/@href').extract()
        for url in next_page_url_list:
            yield Request(
                urljoin_rfc(base_url, url),
                callback=self.parse_category
            )

    def parse_product(self, response):
        base_url = get_base_url(response)

        for url in response.xpath('//p[@id="color_variants"]//a/@href').extract():
	  yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        size_varians = response.xpath('//p[@id="size_variants"]//a/@href').extract()
        for url in size_varians:
	  yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        loader = ProductLoader(item=Product(), response=response)
        price = response.xpath('//b[contains(@class, "pro-price")]/text()').extract()
        if not price:
            return
        price = extract_price_eu(''.join(price[0].split()).strip())

        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        if response.xpath('//span[text()="Obserwuj"]'):
            stock = '0'
        else:
            stock = '1'
        loader.add_value('stock', stock)
        loader.add_xpath('category', '//nav[@id="breadcrumbs"]/a[position()>1]/text()')
        loader.add_xpath('brand', '//*[@id="catalog-info"]//a/b/text()')
        loader.add_value('shipping_cost', "0")
        sku = ' ' + response.xpath('//*[@id="catalog-info"]//b/text()').extract()[-1].strip()
        loader.add_value('sku', sku.strip())
        loader.add_value('identifier', hashlib.md5(sku).hexdigest())
        loader.add_xpath('image_url', '//main[@id="content"]//img/@src')

        product = loader.load_item()

        if product['identifier'] not in self.identifiers_viewed:
            self.identifiers_viewed.append(product['identifier'])
            yield product
