import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.base_spiders.primary_spider import PrimarySpider

from copy import deepcopy
# import copy
# import itertools


class FridgeFreezerDirectSpider(PrimarySpider):
    name = 'cscatering-fridgefreezerdirect.co.uk'
    allowed_domains = ['fridgefreezerdirect.co.uk']
    start_urls = ('https://www.fridgefreezerdirect.co.uk',)

    csv_file = 'fridgefreezerdirect_products.csv'


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        # parse categories
        categories = hxs.select('//div[@id="custommenu"]//div[@class="parentMenu"]/a/@href').extract()
        categories += hxs.select('//ul[@class="categories"]/li/a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))
        # parse products
        products = hxs.select('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            categories = hxs.select('//div[@class="breadcrumbs"]/ul/li[not(@class="home")]/a/text()').extract()
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'categories': categories})

        next_page = hxs.select('//a[contains(@class, "next")]/@href').extract()
        if next_page:
            yield Request(next_page[-1])

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//div[@class="product-name"]/h1/text()').extract()

        identifier = hxs.select('//input[@name="product"]/@value').extract()[0]
        sku = hxs.select('//p[contains(., "SKU")]/b/span/text()').extract()
        sku = sku[0].strip() if sku else ''

        price = hxs.select('//span[@class="price-excluding-tax"]/span[contains(@class, "price")]/text()').extract()
        price = extract_price(price[0])

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('price', price)
        if not loader.get_output_value('price'):
            loader.add_value('stock', 0)
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        for category in response.meta['categories']:
            loader.add_value('category', category)

        brand = hxs.select('//div[@itemprop="brand"]//span[@itemprop="name"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)

        loader.add_value('sku', sku)
        loader.add_value('url', response.url)

        image_url = hxs.select('//div[@class="product-img-box"]/a/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        item = loader.load_item()

        options_config = re.search(r'var spConfig=new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                if attr['code'] == 'config_war':
                    continue

                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  extract_price(option['price'])

            base_price = extract_price(product_data[u'basePrice'])
            for option_identifier, option_name in products.iteritems():
                option_item = deepcopy(item)
                option_item['price'] = base_price + prices[option_identifier]
                option_item['name'] = option_item['name'] + option_name
                option_item['identifier'] = option_item['identifier'] + '-' + option_identifier
                yield option_item
            if not products:
                yield item
        else:
            yield item
