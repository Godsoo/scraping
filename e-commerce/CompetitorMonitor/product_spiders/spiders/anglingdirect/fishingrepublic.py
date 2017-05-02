# -*- coding: utf-8 -*-

import re
import json
from urlparse import urljoin
from scrapy.utils.response import get_base_url
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.contrib.spiders import SitemapSpider
from scrapy.utils.url import add_or_replace_parameter
from scrapy import log
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

#log.start()

class FishingRepublicSpider(SitemapSpider):

    name = 'anglingdirect-fishingrepublic.net'
    allowed_domains = ['fishingrepublic.net']
    sitemap_urls = ['http://www.fishingrepublic.net/sitemap.xml', ]
    top_level_categories = ['bait', 'clothing', 'fishing-kits',
        'game-fly', 'carp', 'coarse', 'sea', 'specialist-pike', ]
    prod_url_re = '|'.join(
        [c + r'/.+?\.html$' for c in top_level_categories]
    )
    sitemap_rules = [('(' + prod_url_re  + ')', 'parse_product')]
    xpath = {
        'breadcrumbs': '//div[@class="breadcrumbs"]//li[@typeof and position()>1]/a/text()',
        'prod_details': '//div[@itemscope]//div[@class="product-view"]',
        'prod_title': './/div[@itemprop="name"]/h1/text()',
        'prod_sku': './/div[@class="sku"]/text()',
        'prod_price': './/span[@itemprop="offers"]//span[@itemprop="price" or @class="price"]/text()',
        'prod_stock': './/link[@itemprop="availability"]/@href',
        'prod_brand': './/tr/th[text()="Manufacturer"]/following-sibling::td/text()',
        'prod_image': './/p[contains(@class, "product-image")]/a/@href',
        'prod_options_1': './/div[@class="product-options"]/dl/following-sibling::script[1]/text()',
        'prod_options_2': './/div[@class="option"]//select/option[position()>1]/text()',
        'prod_id_attribute': './/div[@class="product-options"]//select/@id'
    }
    re = {
        'prod_config': re.compile(r'Product\.Config\(([^)]+)'),
        'prod_id_value': re.compile(r'([\d]+)'),
        'prod_price': re.compile(ur'[(]?\s?£\s?(\d+\.\d+)\s?[)]?'),
    }
    default_shipping_cost = 4.95

    def parse_product(self, response):
        if not response.body:
            return
        hxs = HtmlXPathSelector(response)
        # >>> items.Product
        product_item = Product()
        # >>> product URL
        product_item['url'] = response.url
        # >>> product category
        product_item['category'] = map(
            unicode.strip,
            hxs.select(self.xpath['breadcrumbs']).extract()
        )
        # >>> product details
        prod_details = response.xpath(self.xpath['prod_details'])
        if not self._validate_not_empty('product details', prod_details, response):
            return
        # >>> product name
        prod_name = prod_details[0].select(self.xpath['prod_title']).extract()
        if not self._validate_not_empty('product name', prod_name, response):
            return
        prod_name = prod_name[0].strip()
        # >>> product SKU
        prod_sku = prod_details[0].select(self.xpath['prod_sku']).extract()
        if not self._validate_not_empty('product SKU', prod_sku, response):
            return
        prod_sku = prod_sku[0].strip()
        # >>> product price
        prod_price = prod_details[0].select(self.xpath['prod_price']).re('[\d.,]+')
        if not self._validate_not_empty('product price', prod_price, response):
            return
        price = self._extract_price(prod_price)
        if not self._validate_value('product price', price, response):
            return
        product_item['price'] = price
        # >>> product stock
        prod_stock = prod_details[0].select(self.xpath['prod_stock']).extract()[-1:]
        if not self._validate_not_empty('product stock', prod_stock, response):
            return
        stock = prod_stock[0].strip()
        if stock == 'http://schema.org/InStock':
            product_item['stock'] = 1
        elif stock == 'http://schema.org/OutOfStock':
            product_item['stock'] = 0
        else:
            self.log('Unknown "stock" option', level=log.ERROR)
            return
        # >>> product shipping cost
        product_item['shipping_cost'] = self.default_shipping_cost
        # >>> product brand
        prod_brand = prod_details[0].select(self.xpath['prod_brand']).extract()
        if (
            self._validate_not_empty('product brand', prod_brand, response)
            and
            prod_brand[0].strip().lower() not in ('no', 'unknown', 'n/a')
        ):
            product_item['brand'] = prod_brand[0].strip()
        # >>> product image
        product_item['image_url'] = prod_details[0].select(self.xpath['prod_image']).extract()
        if not self._validate_not_empty('product image', product_item['image_url'], response):
            return
        # >>> product options
        prod_options_1 = prod_details[0].select(self.xpath['prod_options_1']).extract()
        prod_options_2 = prod_details[0].select(self.xpath['prod_options_2']).extract()
        prod_options_3 = hxs.select('//table[@id="super-product-table"]/tbody')
        if prod_options_2:
            for option in prod_options_2:
                prices = self.re['prod_price'].findall(option)
                if prices:
                    product_item['price'] = min(map(float, prices))
                    option = self.re['prod_price'].sub('', option).strip()
                option = re.sub(prod_name, '', option, flags=re.IGNORECASE).strip(' -:')
                # >>> product unique SKU
                product_item['sku'] = prod_sku + ' ' + option
                # >>> product identifier
                product_item['identifier'] = product_item['sku']
                # >>> product name
                product_item['name'] = prod_name + ' ' + option
                # >>> load product
                yield self._load_product(product_item, response)
        elif prod_options_1:
            prod_id_attribute = prod_details[0].select(self.xpath['prod_id_attribute']).extract()
            if not self._validate_not_empty('product id attribute', prod_id_attribute, response):
                return
            prod_id_value = self.re['prod_id_value'].search(prod_id_attribute[0])
            if not self._validate_value('product id value', prod_id_value, response):
                return
            prod_id = prod_id_value.groups()[0]
            js_config = self.re['prod_config'].search(prod_options_1[0])
            if not self._validate_value('JS config', js_config, response):
                return
            try:
                prod_config = json.loads(js_config.groups()[0])
            except ValueError:
                self.log('Cannot parse JSON object :: %s' % response.url, level=log.ERROR)
                return
            try:
                for option in prod_config['attributes'][prod_id]['options']:
                    option = option['label'].replace('  ',' ')
                    # >>> product unique SKU
                    product_item['sku'] = prod_sku + ' ' + option
                    # >>> product identifier
                    product_item['identifier'] = product_item['sku']
                    # >>> product name
                    product_item['name'] = prod_name + ' ' + option
                    # >>> load product
                    yield self._load_product(product_item, response)
            except KeyError:
                self.log('No product options in JSON object', level=log.ERROR)
                return
        elif prod_options_3:
            for option in prod_options_3.select('./tr'):
                product_item['name'] = option.select('./td/text()').extract()
                product_item['sku'] = prod_sku
                product_item['identifier'] = prod_sku + '-' + option.select('.//span[contains(@id, "product-price")]/@id').re('\d+')[0]
                product_item['price'] = option.select('.//span[contains(@id, "product-price")]//text()').extract()
                product_item['stock'] = 0 if option.select('.//p[@class="availability out-of-stock"]') else 1
                yield self._load_product(product_item, response)
        else:
            # >>> product unique SKU
            product_item['sku'] = prod_sku
            # >>> product identifier
            product_item['identifier'] = product_item['sku']
            # >>> product name
            product_item['name'] = prod_name
            # >>> load product
            yield self._load_product(product_item, response)

    def _load_product(self, product_item, response):
        product_loader = ProductLoader(Product(), response=response)
        for key, val in product_item.iteritems():
            product_loader.add_value(key, val)
        return product_loader.load_item()

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

    def _extract_price(self, data):
        for candidate in data:
            try:
                price = float(candidate)
                return price
            except ValueError:
                continue

