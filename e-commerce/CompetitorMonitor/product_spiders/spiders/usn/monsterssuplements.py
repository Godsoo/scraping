# -*- coding: utf-8 -*-

import re
import json
from urlparse import urljoin
from scrapy.utils.response import get_base_url
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.utils.url import add_or_replace_parameter
from scrapy import log
from product_spiders.items import Product, ProductLoader

from product_spiders.base_spiders.primary_spider import PrimarySpider

#log.start()

class MonstersupplementsSpider(PrimarySpider):

    name = "usn-monstersupplements.com"
    allowed_domains = ["monstersupplements.com"]

    csv_file = 'monstersupplements.com_crawl.csv'

    brand_url = 'http://monstersupplements.com/brand/%s.html'
    brands = {
        'Sci-MX': ['Sci-MX'],
        'Optimum Nutrition': ['Optimum Nutrition'],
        'BSN': ['BSN'],
        'PhD': ['PHD Nutrition', 'PHD Woman'],
        'Maxi Nutrition': ['Maxi Nutrition'],
        'Reflex': ['Reflex Nutrition'],
        'Mutant': ['Mutant'],
        'Cellucor': ['Cellucor'],
        'USN': ['USN'],
    }
    xpath = {
        'nav_link': '//div[@class="pages"]//li[@class="item current"]/following-sibling::li[1]/a/@href',
        'prod_link': '//li[@class="item"]//a[@class="product-image"]/@href',
        'category_title': '//div[contains(@class, "category-title")]//h1/text()',
        'breadcrumbs': '//div[@class="breadcrumbs"]//li[contains(@class, "category")]/a/text()',
        'prod_title': '//h1[contains(@class, "product-name")]/text()',
        'prod_price': (
            '//div[@class="item price-info"]//span[contains(@id, "product-price")]/span[@class="price"]/text()',
            '//div[@class="item price-info"]//span[contains(@id, "product-price")]/text()',
            '//div[@class="item price-info"]//span[@class="price"]/text()',
        ),
        'prod_out_stock': '//p[contains(@class, "product-outofstock")]',
        'prod_image': '//img[@id="image-main"]/@src',
    }
    re = {
        'prod_config': re.compile(r'Product\.Config\((.+)\);'),
        'sku': re.compile(r'sku"\s*:\s*"([^"]+)'),
    }

    def start_requests(self):
        for brand, brand_queries in self.brands.items():
            for brand_q in brand_queries:
                yield Request(
                    self.brand_url % brand_q.lower().replace(' ', '-'),
                    callback=self.parse_listing,
                    meta={'brand': brand},
                )

    def parse_listing(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        # >>> ensure brand's page
        category_title = hxs.select(self.xpath['category_title']).extract()
        if not self._validate_not_empty('category title', category_title, response):
            return
        # >>> products
        prod_links = hxs.select(self.xpath['prod_link']).extract()
        if not prod_links:
            return
        for link in prod_links:
            yield Request(
                urljoin(base_url, link),
                callback=self.parse_product,
                meta={'brand': response.meta['brand']},
            )
        # >>> pagination
        nav_link = hxs.select(self.xpath['nav_link']).extract()
        if nav_link:
            yield Request(
                urljoin(base_url, nav_link[0]),
                callback=self.parse_listing,
                meta={'brand': response.meta['brand']},
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_item = Product()
        # >>> product url
        product_item['url'] = response.url
        # >>> product brand
        product_item['brand'] = response.meta.get('brand')
        # >>> product category
        product_item['category'] = hxs.select(self.xpath['breadcrumbs']).extract()[1:]
        if not self._validate_not_empty('product category', product_item['category'], response):
            pass
        # >>> product title
        product_item['name'] = hxs.select(self.xpath['prod_title']).extract()
        if not self._validate_not_empty('product name', product_item['name'], response):
            return
        # >>> product image
        product_item['image_url'] = hxs.select(self.xpath['prod_image']).extract()
        if not self._validate_not_empty('product image', product_item['image_url'], response):
            return
        # >>> product stock
        if hxs.select(self.xpath['prod_out_stock']).extract():
            product_item['stock'] = 0
        else:
            product_item['stock'] = 1
        # >>> product sku/identifier
        sku_match = self.re['sku'].search(response.body)
        if not self._validate_value('product sku', sku_match, response):
            return
        product_item['sku'] = sku_match.groups()[0]
        product_item['identifier'] = product_item['sku']
        # >>> product config
        products = self._parse_config(response)
        if products:
            for prod in products.values():
                product = Product(product_item)
                options = ' '.join(prod['options'])
                product['name'] = product['name'][0] + ' ' + options
                product['sku'] += ' ' + options
                product['identifier'] = product['sku']
                product['price'] = prod['price']
                if product['price'] < 19.99:
                    product['shipping_cost'] = 1.99
                yield self._load_item(product, response)
        else:
            # >>> product price
            for xpath_price in self.xpath['prod_price']:
                price = hxs.select(xpath_price).extract()
                if not price:
                    continue
                else:
                    try:
                        product_item['price'] = float(price[0].strip(u'\r\n£ '))
                        break
                    except ValueError:
                        self.log('Unsupported price value', level=log.ERROR)
                        return
            if not 'price' in product_item:
                self.log('No price elem on the page :: %s' % response.url, level=log.ERROR)
                return
            if product_item['price'] < 19.99:
                product_item['shipping_cost'] = 1.99
            # >>> load item
            yield self._load_item(product_item, response)

    def _load_item(self, product_item, response):
        product_loader = ProductLoader(Product(), response=response)
        for key, val in product_item.iteritems():
            product_loader.add_value(key, val)
        return product_loader.load_item()

    def _parse_config(self, response):
        config = self.re['prod_config'].search(response.body)
        if not config:
            return
        try:
            config_json = json.loads(config.groups()[0])
        except ValueError:
            self.log('Cannot parse JSON object :: %s' % response.url, level=log.ERROR)
            return
        products = {}
        for attr in config_json['attributes'].values():
            if not 'options' in attr:
                continue
            for option in attr['options']:
                label = option['label']
                for product in option['products']:
                    data = products.setdefault(product, {'options': []})
                    data['options'].append(label)
        for product, data in products.items():
            if (
                product not in config_json['productConfig'] or
                'price' not in config_json['productConfig'][product]
            ):
                self.log('Broken productConfig :: %s' % response.url, level=log.ERROR)
                return
            price = self._extract_price(config_json['productConfig'][product]['price'])
            if price is None:
                self.log('Unsupported price value :: %s' % response.url, level=log.ERROR)
                return
            data['price'] = price
        return products

    def _extract_price(self, data):
        try:
            return float(data)
        except ValueError:
            return

    def _validate_not_empty(self, key, value, response):
        if not (value and value[0]):
            self.log('No %s :: %s' % (key, response.url), level=log.ERROR)
            return False
        return True

    def _validate_value(self, key, value, response):
        if value != 0 and not value:
            self.log('No %s :: %s' % (key, response.url), level=log.ERROR)
            return False
        return True

