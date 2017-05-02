import os
import csv

import re

import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from keteritems import KeterMeta, Review, ReviewLoader
import datetime

HERE = os.path.abspath(os.path.dirname(__file__))


def normalize_space(s):
    ''' Cleans up space/newline characters '''
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())

class Spider(ProductCacheSpider):
    name = 'ubaldi.com'
    allowed_domains = ['ubaldi.com']

    def start_requests(self):

        brands = {}
        search_url = 'http://www.ubaldi.com/%s/%s.php'

        with open(HERE+'/brands.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                formatted_brand = row['brand'].lower().replace(' ','-')
                brands[row['brand']] = search_url % (formatted_brand, formatted_brand)

        for brand, url in brands.items():
            yield Request(url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//ul[@class="bloc-menu"]//ul/li/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), meta=response.meta)

        products = hxs.select('//div[contains(@class, "la-infos")]//h2/a/@href').extract()
            
        for product in products:
            request = Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)
            yield request

        next = hxs.select('//link[@rel="next"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(get_base_url(response), next[0]), meta=response.meta)

        for page in hxs.select('//div[@class="menu_lateral"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(response=response, item=Product())

        loader.add_value('url', response.url)
        loader.add_xpath('identifier', '//div[@id="dv_ref"]/@title')
        loader.add_xpath('sku', '//div[@id="dv_ref"]/@title')

        price = hxs.select('//span[contains(@class, "prix")]/@data-prix-origine').extract()
        if not price:
            price = hxs.select('//div[@class="fa-infos-prix"]/div//span[contains(@class, "prix")]/text()').extract()
        price = price[0] if price else 0
        loader.add_value('price', price)

        loader.add_xpath('name', '//h1[@itemprop="name"]//text()')
        categories = hxs.select('//div[@class="breadcrumb"]/span/a/span[@itemprop="title"]/text()').extract()[:-1]
        loader.add_value('category', categories)
        img = ''.join(hxs.select('//img[@itemprop="image"]/@src').extract())
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img))

        loader.add_value('brand', response.meta.get('brand'))

        in_stock = hxs.select('//div[contains(@class, "text-dispo") and contains(text(), "En stock")]')
        if in_stock:
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        product = loader.load_item()
        metadata = KeterMeta()
        metadata['reviews'] = []
        product['metadata'] = metadata

        response.meta['product'] = product
        for x in self.parse_review(response):
            yield x

    def parse_review(self, response, product=None):
        hxs = HtmlXPathSelector(response)
        if not product:
            product = response.meta['product']

        for review in hxs.select('//div[@class="pr-review-main"]'):
            loader = ReviewLoader(item=Review(), selector=review, date_format=u'%Y-%m-%d')
            loader.add_xpath('date', './/span[@itemprop="dtreviewed"]/@datetime')

            loader.add_xpath('full_text', './/div[@class="pr-review-infos-title"]/text()')
            loader.add_xpath('full_text', './/div[@class="pr-comments"]/text()')
            loader.add_value('product_url', product['url'])
            loader.add_value('url', product['url'])
            loader.add_value('sku', product['sku'])
            loader.add_value('rating', len(review.select('.//div[@class="pr-stars pr-stars-small"]/span[contains(@class, "pr-star")]').extract()))
            product['metadata']['reviews'].append(loader.load_item())

        next = hxs.select('//span[@class="pr-page-next"]/a[@href!="#"]/@href').extract()
        if not next:
            yield product
        else:
            yield Request(urljoin_rfc(get_base_url(response), next[0]),callback=self.parse_review, meta=response.meta)

    def add_shipping_cost(self, item):
        item['shipping_cost'] = 0
        return item
