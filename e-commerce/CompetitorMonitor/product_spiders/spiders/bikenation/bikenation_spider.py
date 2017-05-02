# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import add_or_replace_parameter, urljoin_rfc
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
import re
import json
from scrapy import log


def retry_decorator(callback):
    def new_callback(obj, response):
        if response.status in obj.handle_httpstatus_list:
            yield obj._retry_request(response.request)
        else:
            res = callback(obj, response)
            if res:
                for r in res:
                    yield r
    return new_callback


class BikeNationSpider(BaseSpider):
    name = 'bikenation.co.uk-feed'
    allowed_domains = ['www.bikenation.co.uk']
    start_urls = [
        'http://www.bikenation.co.uk/'
    ]
    download_delay = 1
    handle_httpstatus_list = [429]
    max_retry_times = 10

    def _retry_request(self, request):
        retries = request.meta.get('retry_times', 0) + 1
        if retries <= self.max_retry_times:
            retryreq = request.copy()
            retryreq.meta['retry_times'] = retries
            retryreq.meta['recache'] = True
            retryreq.dont_filter = True
            return retryreq
        else:
            self.log('Gave up retrying %(request)s (failed %(retries)d times)' %
                     {'request': request, 'retries': retries})

    @retry_decorator
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="nav"]//li[contains(@class, "level0")]/a/@href').extract():
            url = urljoin_rfc(base_url, url)
            yield Request(add_or_replace_parameter(url, 'limit', '36'), callback=self.parse_products_list)

    @retry_decorator
    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li/a/text() | //div[@class="breadcrumbs"]/ul/li/strong/text()').extract()[1:]
        for url in hxs.select('//div[contains(@class, "category-products")]//div[@class="item-wrap"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'category': category})
        # pagination
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    @retry_decorator
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        redirected_urls = response.meta.get('redirect_urls', None)
        if redirected_urls:
            log.msg('Skips product, redirected url: ' + str(redirected_urls[0]))
            return

        image_url = hxs.select('//a[@id="cloud_zoom"]/img/@src').extract()
        try:
            product_identifier = hxs.select('//input[@name="product"]/@value').extract()[0].strip()
        except:
            product_identifier = hxs.select('//form[@id="product_addtocart_form"]/@action').re(r'/product/(\d+)')[0]
        product_name = hxs.select('//div[@class="product-name"]/h1/text()').extract()[0].strip()
        category = response.meta.get('category')
        brand = hxs.select('//div[contains(@class, "product-shop")]/a/img/@title').extract()
        brand = brand[0].strip() if brand else ''
        out_of_stock = hxs.select('//p[@class="availability out-of-stock"]').extract()

        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))

            for identifier, option_name in products.iteritems():
                product_loader = ProductLoader(item=Product(), selector=hxs)
                sku = product_identifier + '_' + identifier
                product_loader.add_value('identifier', sku)
                product_loader.add_value('sku', sku)
                product_loader.add_value('name', product_name + option_name)
                if image_url:
                    product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                price = float(product_data['basePrice'])
                product_loader.add_value('price', round(price, 2))
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', brand)
                product_loader.add_value('category', category)
                if price < 25:
                    product_loader.add_value('shipping_cost', 2.99)
                else:
                    product_loader.add_value('shipping_cost', 0)
                if out_of_stock:
                    product_loader.add_value('stock', 0)
                product = product_loader.load_item()
                yield product
        else:
            product_loader = ProductLoader(item=Product(), selector=hxs)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('sku', product_identifier)
            product_loader.add_value('name', product_name)
            if image_url:
                product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            price = hxs.select('//*[@id="product-price-{}"]//text()'.format(product_identifier)).extract()
            price = ''.join(price).strip()
            if price == '':
                price = hxs.select('//*[@id="old-price-{}"]//text()'.format(product_identifier)).extract()
                price = ''.join(price).strip()
            price = extract_price(price)
            product_loader.add_value('price', price)
            product_loader.add_value('url', response.url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            if price < 25:
                product_loader.add_value('shipping_cost', 2.99)
            else:
                product_loader.add_value('shipping_cost', 0)
            if out_of_stock:
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
            yield product
