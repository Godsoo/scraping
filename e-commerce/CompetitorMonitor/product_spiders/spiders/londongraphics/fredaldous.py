# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from product_spiders.items import Product, ProductLoader

from product_spiders.utils import extract_price
import re
import json


class FredaldousSpider(BaseSpider):

    name = u'fredaldous.co.uk'
    allowed_domains = ['www.fredaldous.co.uk']
    start_urls = ('http://www.fredaldous.co.uk/?PageSpeed=noscript',)
    identifiers = []

    def parse(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = filter(lambda u: u.strip() != '#', hxs.select('//ul[@id="mainnav"]/li//a/@href').extract())
        for url in urls:
            url = urljoin_rfc(base_url, url)
            url = add_or_replace_parameter(url, 'PageSpeed', 'noscript')
            yield Request(url, callback=self.parse_products)


    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = hxs.select('//div[@class="category-title-h1"]/h1/text()').extract()
        if category:
            category = category[0].strip()
        else:
            category = ''

        urls = hxs.select('//div[@class="pages"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products)

        urls = hxs.select('//h4[@class="product_name"]/a/@href').extract()

        for url in urls:
            url = urljoin_rfc(base_url, url)
            url = add_or_replace_parameter(url, 'PageSpeed', 'noscript')
            yield Request(url, callback=self.parse_product, meta={'category': category})


    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brand = hxs.select('//meta[@property="og:brand"]/@content').extract()
        brand = brand[0] if brand else ''
        category = response.meta.get('category', '')

        product_config_reg = re.search('var spConfig=new Product.Config\((.*)\).*var original_product_name;', response.body, flags=re.DOTALL)
        if not product_config_reg:
            product_config_reg = re.search('var spConfig = new Product.Config\((.*)\).*var original_product_name;', response.body, flags=re.DOTALL)
        if not product_config_reg:
            product_config_reg = re.findall(re.compile('var spConfig = new Product.Config\((.*)\).*'), response.body)
            product_config_reg = product_config_reg[0] if product_config_reg else ''

        if product_config_reg:

            try:
                products = json.loads(product_config_reg.group(1))
            except:
                products = json.loads(product_config_reg)

            for attr_id, attribute in products[u'attributes'].items():
                for option in attribute['options']:
                    option = option['productsData'][0]
                    loader = ProductLoader(item=Product(), response=response)
                    loader.add_value('identifier', option[0])
                    loader.add_value('url', response.url)
                    loader.add_value('image_url', option[3][0] if option[3] else '')
                    loader.add_value('brand', brand)
                    loader.add_value('category', category)
                    loader.add_value('stock', option[4])
                    loader.add_value('name', option[5])
                    loader.add_value('shipping_cost', extract_price(option[6]))
                    loader.add_value('price', option[2])
                    loader.add_value('sku', option[1])

                    item = loader.load_item()

                    if item['identifier'] not in self.identifiers:
                        self.identifiers.append(item['identifier'])
                        yield item

        else:
            stock = hxs.select('//span[@class="stock_value"]/span/text()').re(r'(\d+)')
            price = hxs.select('//span[contains(@id, "product-price-")]/span[@class="price"]/text()').extract()
            if not price:
                price = hxs.select('//span[contains(@id, "product-price-") and @class="price"]/text()').extract()
            if not price:
                price = hxs.select('//span[contains(@class, "old-price")]/span[@class="price"]/text()').extract()
            shipping_cost = hxs.select('//span[contains(@id, "product-price-")]/span[contains(@class, "price-delivery")]/text()').extract()
            if not shipping_cost:
                shipping_cost = hxs.select('//span[contains(@id, "product-price-") and contains(@class, "price")]'
                    '/following-sibling::span[contains(@class, "price-delivery")]/text()').extract()

            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('identifier', '//input[@name="product"]/@value')
            loader.add_value('url', response.url)
            loader.add_xpath('image_url', '//div[@id="product-images"]//img[@class="img-responsive"]/@src')
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            if stock:
                loader.add_value('stock', stock[0])
            else:
                loader.add_value('stock', 0)
            loader.add_xpath('name', '//div[contains(@class, "product-name")]/*[self::h1 or self::h2]/text()')
            loader.add_value('shipping_cost', shipping_cost)
            loader.add_value('price', price)
            loader.add_xpath('sku', '//div[contains(@class, "product-name")]//span[@class="sku_value"]/text()')

            item = loader.load_item()
            if 'identifier' not in item:
                self.log("Warning: no identifier found, skiping product")
                return
            if item['identifier'] not in self.identifiers:
                self.identifiers.append(item['identifier'])
                yield item
