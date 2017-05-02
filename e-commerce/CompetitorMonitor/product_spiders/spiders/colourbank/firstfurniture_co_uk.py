# -*- coding: utf-8 -*-

import re
import json
from scrapy import Spider, Request
from product_spiders.utils import extract_price2uk
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)


class FirstFurniture(Spider):
    name = 'firstfurniture.co.uk'
    allowed_domains = ['firstfurniture.co.uk']
    start_urls = ['https://www.firstfurniture.co.uk/']


    def parse(self, response):
        category_urls = response.xpath('//a[contains(@class, "itemMenuName")]/@href').extract()
        for url in category_urls:
            yield Request(response.urljoin(url), callback=self.parse_category)

    def parse_category(self, response):
        next_page = response.xpath('//a[@title="Next"]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]), callback=self.parse_category)

        product_urls = response.xpath('//h2[@class="product-name"]/a/@href').extract()
        for url in product_urls:
            yield Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        price = response.css('div.pprice .price ::text').extract()
        if price:
            price = extract_price2uk(price[0])
            stock = 1
        else:
            price = 0
            stock = 0
        in_stock = bool(response.xpath('//*[contains(@class, "availability") and contains(@class, "in-stock")]'))
        if not in_stock:
            stock = 0
        identifier = response.xpath('//input[@name="product"]/@value').extract()
        sku = map(unicode.strip, response.xpath('//div[@class="product-name"]/*[@class="sku_prd"]/text()').re(r'Product Code:(.*)'))
        category = filter(lambda s: bool(s),
                          map(unicode.strip,
                              response.xpath('//*[@itemtype="http://schema.org/BreadcrumbList"]'
                                             '//*[contains(@itemprop, "name")]/text()').extract()))[1:-1]

        name = response.xpath('//div[@class="product-name"]/h1/text()').extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('stock', stock)
        loader.add_xpath('brand', '//div[@class="product-essential"]//a[@class="man_img"]/@title')
        loader.add_value('identifier', identifier)
        loader.add_value('sku', sku)
        loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')
        loader.add_value('shipping_cost', 0)
        loader.add_value('url', response.url)
        loader.add_value('category', category)
        main_product = loader.load_item()

        option_boxes = response.xpath('//div[@id="product-options-wrapper"]//select')
        if option_boxes:
            product_config = re.findall(string=response.body, pattern=r'var spConfig = new Product.Config\((.*)?\);')
            if product_config:
                product_data = json.loads(product_config[0])
                products = {}
                for attr in product_data['attributes'].itervalues():
                    for option in attr['options']:
                        for opt_id in option['products']:
                            products[opt_id] = ' - '.join((products.get(opt_id, ''), option['label']))
                for identifier, option_name in products.iteritems():
                    new_item = Product(main_product)
                    new_item['identifier'] += '_' + identifier
                    new_item['name'] += option_name
                    yield new_item
        else:
            yield main_product


    def get_option(self, response):
        product = response.meta['product']
        data = json.loads(response.body)
        product['price'] = extract_price2uk(data['unformattedPrice'])
        if data['combinationid']:
            product['identifier'] = response.meta['id'] + '-' + data['combinationid']
        else:
            product['identifier'] = response.meta['id']
        product['name'] = response.meta['name']
        yield product

    def get_name(self, s):
        return re.findall(ur'(\w.+?)[(£]', s)[0]
