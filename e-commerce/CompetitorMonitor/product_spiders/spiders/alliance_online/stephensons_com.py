# -*- coding: utf-8 -*-


"""
Account: Alliance Online
Name: stephensons.com
"""


import os
import re
import csv
from decimal import Decimal
from scrapy import Spider, Request
from scrapy.http import HtmlResponse
from scrapy.contrib.loader.processor import TakeFirst, Compose
from product_spiders.items import Product, ProductLoader
from product_spiders.config import DATA_DIR


def extract_price(text):
    price_str = re.sub('(?u)(\d),(\d)', '\\1\\2', text)
    match_obj = re.search('([.0-9]+)', price_str)
    if match_obj:
        return match_obj.group(1)
    else:
        return 0


class StephenSons(Spider):
    name = 'stephensons.com'
    allowed_domains = ['www.stephensons.com']
    start_urls = ('http://www.stephensons.com/sitemap',)

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def start_requests(self):
        self.products_cache = {}
        filename = self._get_prev_crawl_filename()
        if filename and os.path.exists(filename):
            with open(filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.products_cache[row['identifier']] = {
                        'sku': row.get('sku', '').decode('utf-8'),
                        'image_url': row.get('image_url', '').decode('utf-8'),
                    }

        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        categories = response.xpath('//div[@class="categTree" and h3/text()="Categories"]/ul[@class="tree"]/li/a/@href').extract()

        for url in categories:
            yield Request(url, callback=self.parse_category)


    def parse_category(self, response):
        # more categories
        categories = response.xpath(u'//div[@id="subcategories"]/ul/li//a[1]/@href').extract()
        for category in categories:
            url = response.urljoin(category)
            yield Request(url, callback=self.parse_category)

        # products
        products = response.xpath(u'//ul[@id="product_list"]/li')
        products_category = list(set(response.xpath(u'//div[@class="breadcrumb" and position()=1]/a[not(position()=1)]/text()').extract() + \
                                     [response.xpath(u'//div[@class="breadcrumb" and position()=1]//text()').extract()[-1]]))
        for product_xs in products:
            pack_price = product_xs.xpath('.//span[@class="price-pack"]//text()').re(r'[\d\,.]+')
            price = product_xs.xpath('.//span[@class="price"]/text()').re(r'[\d\,.]+')
            loader = ProductLoader(item=Product(), selector=product_xs)
            loader.add_xpath('identifier', './/h3/a/@href', re=r'/(\d+)-')
            loader.add_xpath('name', './/h3/a/text()')
            loader.add_xpath('url', './/h3/a/@href')
            loader.add_value('category', products_category)
            loader.add_value('price', pack_price[-1] if pack_price else price[-1])
            price = loader.get_output_value('price')
            if price:
                loader.add_value('shipping_cost', Decimal('4.95') if price < Decimal('50') else Decimal('0.0'))
            in_stock = bool(product_xs.xpath('.//img[@class="ticky-tick" and (@alt="product in stock" or contains(@alt, "days"))]'))
            loader.add_value('stock', 1 if in_stock else 0)

            item = loader.load_item()
            item['metadata'] = {'product_code': item['identifier']}

            item = loader.load_item()

            if item['identifier'] in self.products_cache:
                self.log('Product found in cache => %s' % item['identifier'])
                item['sku'] = self.products_cache[item['identifier']]['sku']
                item['image_url'] = self.products_cache[item['identifier']]['image_url']
                yield item
            else:
                self.log('Product NOT found in cache => %s' % item['identifier'])
                yield Request(item['url'], callback=self.parse_product)

        if not products:
            meta = response.meta.copy()
            meta['retry'] = meta.get('retry', 0)
            if meta['retry'] < 3:
                meta['retry'] += 1
                self.log('>>> RETRY %d => %s' % (meta['retry'], response.request.url))
                yield Request(response.request.url, meta=meta)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return

        categories = response.xpath(u'//div[@class="breadcrumb" and position()=1]/a[not(position()=1)]/text()').extract()
        image_url = response.xpath(u'//div[@id="image-block" and position()=1]/img/@src').extract()
        if image_url:
            image_url = response.urljoin(image_url[0])

        name = response.xpath(u'//div[@id="primary_block"]/h1[1]/text()').extract()[0]

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('name', name.strip())
        product_loader.add_value('url', response.url)
        for category in categories:
            product_loader.add_value('category', category)
        product_loader.add_value('image_url', image_url)

        price = product_loader.get_xpath('//p[@class="price"]/span[@class="our_price_display"]/text()',
                                         TakeFirst(), Compose(extract_price))
        price_excl_vat = Decimal(price)

        product_loader.add_value('price', price_excl_vat)

        product_loader.add_value('shipping_cost', Decimal('4.95') if price_excl_vat < 50 else Decimal('0.0'))
        product_loader.add_xpath('sku', '//p[@id="product_reference"]/span[@class="editable"]/text()')
        product_loader.add_xpath('identifier', '//input[@name="id_product"]/@value', TakeFirst())
        in_stock = response.xpath(u'//form[@id="buy_block"]/following-sibling::p/img[contains(@alt, "in stock")]').extract()
        if not in_stock:
            in_stock = response.xpath(u'//div[@id="pb-left-column"]//img[contains(@alt, "days")]').extract()
        normally_available = response.xpath(u'//form[@id="buy_block"]/following-sibling::img[contains(@alt, "Available")]/@alt').extract()
        call_for_details = response.xpath(u'//form[@id="buy_block"]/following-sibling::img[contains(@alt, "Call for Details")]/@alt').extract()

        product_loader.add_value('stock', 1 if in_stock or normally_available or call_for_details else 0)

        item = product_loader.load_item()

        item['metadata'] = {
            'product_code': ''.join(response.xpath('//input[@name="id_product"]/@value').extract())
        }

        yield item
