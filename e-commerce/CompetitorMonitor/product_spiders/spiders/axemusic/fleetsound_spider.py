"""
IMPORTANT

This site is blocking using Cloudfare, the IP was set in /etc/hosts and the items are now extracted from a single list.

"""

import re
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product
from axemusic_item import ProductLoader


class FleetSoundSpider(BaseSpider):
    name = 'fleetsound.com'
    allowed_domains = ['fleetsound.com']
    start_urls = ['https://fleetsound.com/ajaxlayerednavigation/shopby/f/NEW.html?limit=48&mode=grid']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]), callback=self.parse_products)

        # categories = hxs.select('//dl[@id="narrow-by-list"]/dt[contains(text(), "Category")]/following-sibling::dd[1]//a[@class="ajax-option-link"]')
        # for category in categories:
            # name = category.select('text()').extract()[0].strip()
            # url = category.select('@href').extract()[0]
            # yield Request(urljoin_rfc(base_url, url), callback=self.parse_products, meta={'category': name})

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        category = response.meta.get('category', '')

        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(url, callback=self.parse_products, meta=response.meta)

        products = hxs.select('//li[contains(@class, "item")]')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            try:
                model = map(unicode.strip, product.select('.//p[contains(text(), "model: ")]/text()').re(r'model: (.*)'))[0]
            except:
                model = ''
            name = product.select('.//h2[@class="product-name"]/a/text()').extract()
            if name:
                name = name[0].strip()
            else:
                name = ''
            loader.add_value('name', ' '.join((name, model)))
            url = product.select('.//h2[@class="product-name"]/a/@href').extract()[0].strip()
            identifier = product.select('.//span[contains(@id, "product-price-")]/@id').re(r'product-price-(\d+)')
            if not identifier:
                identifier = product.select('.//ul[@class="add-to-links"]/li/a[@class="link-compare" or @class="link-wishlist"]/@href').re('product/(.*?)/')
            if identifier:
                prod_id = identifier[0]
                loader.add_value('identifier', prod_id)
            loader.add_value('url', url.split('?')[0])
            try:
                brand = map(unicode.strip, product.select('.//p[contains(text(), "manufacturer: ")]/text()').re(r'manufacturer: (.*)'))[0]
            except:
                brand = product.select('td[3]//text()').extract()
            loader.add_value('brand', brand)
            if model:
                loader.add_value('sku', model)
            image_url = product.select('.//a[@class="product-image"]/img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            try:
                price = product.select('.//span[contains(@id, "product-price-")]/span[@class="price"]/text()').extract()[0].strip()
            except:
                try:
                    price = product.select('.//span[contains(@id, "product-price-") and contains(@class, "price")]/text()').extract()[0].strip()
                except:
                    price = '0.0'
            loader.add_value('price', price)

            loader.add_value('category', category)

            if loader.get_collected_values('identifier') and loader.get_collected_values('identifier')[0]:
                product = loader.load_item()
                if product['price'] > 0:
                    yield product
            else:
                self.log('IDENTIFIER NOT FOUND!!! {}'.format(loader.get_output_value('url')))
                # yield Request(url, meta={'loader':loader}, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        loader = response.meta['loader']
        identifier = hxs.select('//input[@name="product"]/@value').extract()
        loader.add_value('identifier', identifier)
        product = loader.load_item()
        if product['price'] > 0:
            yield product
