# -*- coding: utf-8 -*-

import os
import pandas as pd
from decimal import Decimal
from scrapy import Spider, Request
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from product_spiders.config import DATA_DIR


class HandtecCoUkSpider(Spider):
    name = u'handtec.co.uk'
    allowed_domains = ['www.handtec.co.uk']
    start_urls = ['http://www.handtec.co.uk']

    rotate_agent = True
    download_delay = 5

    def __init__(self, *args, **kwargs):
        super(HandtecCoUkSpider, self).__init__(*args, **kwargs)

        self.products_cache_filename = ''
        self.products_cache = None

    def spider_idle(self, spider):
        if self.products_cache is not None:
            not_viewed = self.products_cache[self.products_cache['viewed'] == False]
            for i, row in not_viewed.iterrows():
                request = Request(row['url'], callback=self.parse_product)
                self._crawler.engine.crawl(request, self)
            self.products_cache = None

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            self.products_cache_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            self.products_cache = pd.read_csv(self.products_cache_filename, dtype=pd.np.str)
            self.products_cache = self.products_cache.where(pd.notnull(self.products_cache), None)
            self.products_cache['viewed'] = False

        yield Request(self.start_urls[0])

    def parse(self, response):
        categories = response.xpath('//ul[contains(@class, "mega-menu-list")]/li/a')
        for cat in categories:
            url = cat.select('@href').extract_first()
            name = cat.select('text()').extract_first()
            yield Request(response.urljoin(url), callback=self.parse_products, meta={'category': [name]})

        for url in response.xpath('//div[@class="paginationControl"]//a[contains(text(), "Next")]/@href').extract():
            yield Request(url)

    def parse_products(self, response):
        # subcategories
        urls = response.xpath('//div[@class="layerd_block"]/h2[text()="Category"]/..//a/@href').extract()
        subcats = None #response.xpath('//div[@class="layerd_block"]/h2[text()="Category"]/..//a/text()').extract()
        category = response.meta.get('category', [])
        if subcats:
            for url, cat in zip(urls, subcats):
                c = list(category)
                c.append(cat.strip())
                yield Request(response.urljoin(url), callback=self.parse_products, meta={'category': c})
        else:
            products = response.xpath('//section[@class="products"]//li[contains(@class, "item")]')
            for product in products:
                identifier = product.select('.//span[contains(@id, "price-including-tax-")]/@id').re(r'\d+')
                price = product.select('.//span[contains(@id, "price-including-tax-")]/text()').re(r'[\d,.]+')
                product_url = product.select('.//div[@class="pro_name"]/a/@href').extract()[0]
                if identifier and price and (self.products_cache is not None):
                    cached_item = self.products_cache[self.products_cache['identifier'] == identifier[0]]
                    if not cached_item.empty:
                        cached_item_dict = dict(cached_item.iloc[0])
                        del cached_item_dict['viewed']
                        cached_product = Product(cached_item_dict)
                        cached_product['price'] = Decimal(extract_price(price[0]))
                        del cached_product['dealer']
                        if cached_product['name'] is None:
                            del cached_product['name']
                        if cached_product['category'] is None:
                            del cached_product['category']
                        if cached_product['shipping_cost']:
                            cached_product['shipping_cost'] = Decimal(cached_product['shipping_cost'])
                        else:
                            del cached_product['shipping_cost']
                        in_stock = bool(product.select('.//div[contains(@class, "instock") or contains(@class, "duesoon")]'))
                        if not in_stock:
                            cached_product['stock'] = 0
                        else:
                            del cached_product['stock']
                        self.products_cache['viewed'].loc[cached_item.index] = True
                        yield cached_product
                    else:
                        yield Request(response.urljoin(product_url), callback=self.parse_product, meta={'category': category})
                else:
                    yield Request(response.urljoin(product_url), callback=self.parse_product, meta={'category': category})

            # Pages
            for url in response.xpath('//div[@class="pages"]//a/@href').extract():
                yield Request(response.urljoin(url), callback=self.parse_products, meta={'category': category})

    def parse_product(self, response):
        image_url = response.xpath('//*[@id="imgPath"]/@href').extract()
        product_identifier = response.xpath('//*[@id="links[relatedfaqs]"]/@value').extract()
        if not product_identifier:
            product_identifier = response.xpath('//input[@name="product"]/@value').extract()
        product_identifier = product_identifier[0]
        product_name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        price = response.xpath(
            '//div[@class="price-box"]//span[contains(@id, '
            '"price-including-tax-{}")]/text()'.format(product_identifier)).extract()
        price = extract_price(price[0]) if price else 0
        category = response.meta.get('category')
        brand = response.xpath('//span[@itemprop="brand"]/span/text()').extract()
        brand = brand[0] if brand else ''
        sku = response.xpath('//meta[@itemprop="sku"]/@content').extract()[0]
        product_loader = ProductLoader(item=Product(), response=response)
        stock_url = None
        stock = None
        try:
            stock = response.xpath('//div[@class="detail_instock"]/text()').extract()[0]
        except:
            for l in response.body.split('\n'):
                if 'blockTag' in l:
                     stock_url = l.split('esiUrl = "')[-1][:-3].replace('\\', '')
                     break
        if stock is not None and 'In Stock' not in stock:
            product_loader.add_value('stock', 0)

        product_loader.add_value('identifier', product_identifier)
        product_loader.add_value('name', product_name)
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url[0]))
        product_loader.add_value('sku', sku)
        product_loader.add_value('price', price)
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        product_loader.add_value('brand', brand)
        product_loader.add_value('shipping_cost', 1.99)

        product = product_loader.load_item()

        if stock is None and stock_url is not None:
            yield Request(stock_url, callback=self.parse_stock, meta={'item': product})
        else:
            yield product

    def parse_stock(self, response):
        product = Product(response.meta['item'])
        in_stock = bool(response.xpath('//*[@itemprop="availability" and @href="http://schema.org/InStock"]'))
        if not in_stock:
            product['stock'] = 0

        yield product
