# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
import urllib
import re
import json
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


class RymanSpider(BaseSpider):
    name = u'ryman.co.uk'
    allowed_domains = ['www.ryman.co.uk']
    start_urls = ('http://www.ryman.co.uk/', )
    identifiers = []
    categories = []

    def __init__(self, *args, **kwargs):
        super(RymanSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if spider != self: 
            return
        if self.categories:
            self._crawler.engine.crawl(Request(self.categories.pop(), callback=self.parse_products_list, dont_filter=True), self)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        urls = hxs.select('//div[@class="navbar-inner"]//div[@class="navdropdown-block"]/a[position()>1]/@href').extract()
        categories = hxs.select('//div[@class="navbar-inner"]//div[@class="navdropdown-block"]/a[position()>1]/text()').extract()
        for url, category in zip(urls, categories):
            full_url = urljoin_rfc(base_url, url)
            self.categories.append(full_url)
            yield Request(full_url, callback=self.parse_brands_in_category, meta={'category': category})
    
    def parse_brands_in_category(self, response):
        hxs = HtmlXPathSelector(response)
        for brand in hxs.select('//dt[text()="Brand"]/following-sibling::dd[1]/ol/li/a'):
            name = brand.select('text()').extract()[0].strip()
            url = brand.select('@href').extract()[0]
            yield Request(url, callback=self.parse_products_list, meta={'brand':name})
            
    def parse_brands(self, response):
        hxs = HtmlXPathSelector(response)
        for brand in hxs.select('//a[text()="Shop by Brand"]/following-sibling::div//a'):
            yield Request(brand.select('@href').extract()[0], callback=self.parse_products_list, meta={'brand':brand.select('text()').extract()[0]})
            
    def parse_products_list(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        urls = hxs.select('//div[@class="pages"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list, meta=response.meta)
        urls = hxs.select('//div[@class="category-products"]//h2/a/@href').extract()
        for url in urls:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        brand = response.meta.get('brand')
        category = response.meta.get('category')
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li[position()>1]/a/text()').extract()
        url = response.url

        identifier = hxs.select('//*[@id="product_addtocart_form"]//input[@name="product"]/@value').extract()
        if not identifier:
            return
        identifier = identifier[0]

        price = hxs.select('//span[@id="price-including-tax-{}"]/text()'.format(identifier)).extract()[0].strip()
        price = extract_price(price)

        name = hxs.select('//div[@class="product-name"]/span[@class="h1"]/text()').extract()
        name = ''.join(name).strip()

        product_options = []
        conf_data = re.search(r'new Product.Config\((.*)\)', response.body)
        if conf_data:
            product_data = json.loads(conf_data.group(1))
            if product_data:
                for attribute in product_data['attributes'].itervalues():
                    for option in attribute['options']:
                        product_options.append(option)
            
        if len(product_options)<=1:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', identifier)
            loader.add_value('url', response.url)
            loader.add_value('brand', brand)
            loader.add_value('category', category)
            loader.add_value('price', price)
            loader.add_value('name', name)
            sku = hxs.select('//div[@class="ry-simple-sku"]/strong[1]/text()').extract()
            loader.add_value('sku', sku)
            image_url = hxs.select('//img[@id="image-main"]/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            stock = hxs.select('//div[@class="stockmsg_productview"]').extract()
            if stock:
                loader.add_value('stock', 0)
            if price <= 29.99:
                loader.add_value('shipping_cost', 2.9)
            else:
                loader.add_value('shipping_cost', 0)
            yield loader.load_item()
        else:
            images = hxs.select('//script[@type="text/javascript"]/text()').re('base_image":({.+?})')
            if images:
                images = json.loads(images[0])
            for option in product_options:
                for identifier in option['products']:
                    if identifier not in self.identifiers:
                        loader = ProductLoader(item=Product(), selector=option)
                        loader.add_value('identifier', identifier)
                        loader.add_value('url', url)
                        loader.add_value('brand', brand)
                        loader.add_value('category', category)
                        loader.add_value('name', name +' ' + option['label'])
                        sku = hxs.select('//div[@id="%s"]/strong[1]/text()' %option['id']).extract()[0]
                        loader.add_value('sku', sku)
                        option_price = price + extract_price(option['price'])
                        loader.add_value('price', option_price)
                        if option_price <= 29.99:
                            loader.add_value('shipping_cost', 2.9)
                        product = loader.load_item()
                        if images:
                            image_url = images[identifier]
                        else:
                            image_url = hxs.select('//script[@type="text/javascript"]/text()').re("var images%s.+Array.+?,(.+?)'" %option['id'])
                        loader.add_value('image_url', image_url)
                        yield loader.load_item()

    def parse2(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        product = response.meta['product']
        if product['identifier'] in self.identifiers:
            return
        self.identifiers.append(product['identifier'])
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('identifier', product['identifier'])
        loader.add_value('url', product['url'])
        loader.add_value('brand', product['brand'])
        loader.add_value('category', product['category'])
        loader.add_value('price', product['price'])
        loader.add_value('name', product['name'])
        loader.add_value('sku', product['sku'])
        image_url = hxs.select('//*[@id="zoom1"]/img/@src').extract()
        if not image_url:
            image_url = hxs.select('//p[@class="product-image"]/img/@src').extract()
        loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        if product['price'] <= 29.99:
            loader.add_value('shipping_cost', 2.9)
        else:
            loader.add_value('shipping_cost', 0)
        yield loader.load_item()
