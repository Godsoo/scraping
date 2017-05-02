# -*- coding: utf-8 -*-
import json
from decimal import Decimal
import itertools

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
import re


class MedisaveSpider(BaseSpider):
    name = u'medisave.co.uk'
    allowed_domains = ['medisave.co.uk']
    start_urls = ['http://www.medisave.co.uk/diagnostics-equipment.html?limit=64',
                  'http://www.medisave.co.uk/furniture-fittings.html?limit=64',
                  'http://www.medisave.co.uk/consumables-general-supplies.html?limit=64']
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        items = hxs.select('//div[contains(@class, "category-products")]/ul/li')
        for item in items:
            price = item.select('.//div[@class="price-box"]')
            url = item.select('.//h2[@class="product-name"]/a/@href').extract().pop()
            if price:
                yield Request(urljoin(base_url, url), callback=self.parse_product)

        for url in hxs.select('//ul[@class="subcategories"]/li/a/@href').extract():
            yield Request(url)
        urls = hxs.select('//div[@class="pages"]//a/@href').extract()
        for url in urls:
            yield Request(urljoin(base_url, url), callback=self.parse)


    def retry(self, response, error="", retries=3):
        retry = int(response.meta.get('retry', 0))
        if retry < retries:
            retry = retry + 1
            yield Request(response.request.url, dont_filter=True,
                          meta={'retry': retry, 'recache': True})
        else:
            self.errors.append(error)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        name = hxs.select('//div[@class="product-name"]/span[@class="h1"]/text()').extract()
        if not name:
            self.retry(response, "Cant find name on " + response.url)
            return
        name = name.pop().strip()
        category = hxs.select('//div[@class="breadcrumbs"]/ul/li[2]/a/text()').extract()
        identifier = hxs.select('//*[@id="product_addtocart_form"]//input[@name="product"]/@value').extract()[0].strip()
        sku = hxs.select('//span[@itemprop="productID"]/text()').extract()
        if not sku:
            sku = hxs.select('//span[@itemprop="model"]/text()').extract() or hxs.select('//meta[@itemprop="productID"]/@content').extract()
        if not sku:
            sku = hxs.select('//script/text()').re("g_ecomm_prodid = '(.+)'")
        brand = hxs.select('//div[@class="manufacturer-logo"]/img/@title').extract()
        price = hxs.select('//*[@id="price-excluding-tax-{}"]/text()'.format(identifier)).extract()
        if price:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            image_url = hxs.select('//div[@class="product-img-box"]//img/@src').extract()
            if image_url:
                loader.add_value('image_url', urljoin(base_url, image_url[0]))
            if category:
                loader.add_value('category', category[-1])
            loader.add_value('identifier', identifier)
            loader.add_value('price', extract_price(price.pop().strip()))
            if sku:
                loader.add_value('sku', sku[0])
            availability = hxs.select('//*[@id="product-stock"]/text()').extract()
            if availability:
                availability = availability[0].strip()
                stock_level = ''
                for match in re.finditer(r"([\d]+)", availability):
                    if len(match.group()) > len(stock_level):
                        stock_level = match.group()
                if stock_level:
                    loader.add_value('stock', stock_level)
            if brand:
                loader.add_value('brand', brand[0])

            product = loader.load_item()

            config = response.xpath('//script/text()').re('Product.Config\((.+)\);')
            if config:
                data = json.loads(config[0])
                baseprice = Decimal(data['basePrice'])
                options = []
                attributes = data['attributes']
                for attribute_id in attributes:
                    options.append(attributes[attribute_id]['options'])
                variants = itertools.product(*options)
                for variant in variants:
                    item = Product(product)
                    item['price'] = baseprice
                    for option in variant:
                        item['identifier'] += '-' + option['id']
                        item['name'] += ' ' + option['label'].strip()
                        item['price'] += Decimal(option['price'])
                        if len(option.get('products', [])) > 0:
                            image_url = hxs.select('//img[contains(@id,"imageConfigurable{}")]/@src'.format(option['products'][0])).extract()
                            if image_url:
                                item['image_url'] = image_url[0]
                    yield Product(item)
                return
            yield product
        else:
            for product in hxs.select('//table[@id="super-product-table"]/tbody/tr'):
                name = "".join(product.select("td/text()").extract()).replace("SKU:", "").strip()
                image_url = product.select("td/img/@src").extract()
                sku = product.select('//span[@itemprop="model"]/text()').extract()
                subid = product.select("td/input/@name").re("[^0-9]*([0-9]+)[^0-9]*").pop()
                price = product.select('td//span[@itemprop="price"]/text()').extract().pop().strip()

                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('url', response.url)
                loader.add_value('name', name)
                if image_url:
                    loader.add_value('image_url', urljoin(base_url, image_url.pop()))
                if category:
                    loader.add_value('category', category[-1])
                loader.add_value('identifier', identifier + subid)
                loader.add_value('price', extract_price(price))
                if brand:
                    loader.add_value('brand', brand[0])
                if sku:
                    loader.add_value('sku', sku[0])
                yield loader.load_item()
