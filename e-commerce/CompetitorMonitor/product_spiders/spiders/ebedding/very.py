# -*- coding: utf-8 -*-
"""
Account: E-Bedding
Name: e-bedding-very.co.uk
Ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4955

Extract all products including product options only from the "Bedding" sub category

"""

import re
import json

from scrapy import Spider
from scrapy.http import Request
from urlparse import urljoin
from product_spiders.utils import extract_price

from scrapy.utils.url import url_query_cleaner

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class VeryCoUk(Spider):
    name = "e-bedding-very.co.uk"
    allowed_domains = ["very.co.uk"]
    start_urls = ['http://www.very.co.uk/home-garden/bedding/e/b/13042.end']

    def parse(self, response):

        products = response.xpath('//a[@class="productTitle"]/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

        next = response.xpath('//a[@class="paginationNext"]/@href').extract()
        if next:
            yield Request(response.urljoin(next[0]))

    def parse_product(self, response):

        loader = ProductLoader(item=Product(), response=response)
        categories = response.xpath('//ul[@class="breadcrumbList"]/li[@itemprop="itemListElement"]//span[@itemprop="name"]/text()').extract()[1:]
        loader.add_value('category', categories)
        brand = response.xpath('//script[@type="text/javascript"]/text()').re('brand: *\"(.+)\"')
        loader.add_value('brand', brand)
        loader.add_xpath('image_url', '//div[@id="amp-originalImage"]/img/@src')
        loader.add_value('url', url_query_cleaner(response.url))
        loader.add_xpath('name', '//input[@name="speedtrapProductDisplayName"]/@value')
        identifier = response.xpath('//text()').re("productId: '(.*)'")[0]
        loader.add_value('identifier', identifier)
        sku = response.xpath('//span[@id="productEAN"]/text()').extract()
        sku = sku[-1].strip() if sku else ''
        loader.add_value('sku', sku)
        loader.add_xpath('price', '//input[@name="speedtrapPrice"]/@value')
        stock = 1 if response.xpath('//meta[@property="product:availability"]/@content[.="In Stock"]') else 0
        loader.add_value('stock', stock)
        loader.add_value('shipping_cost', 3.99)
        item = loader.load_item()

        options = response.xpath('//ul[@class="productOptionsList"]/li[contains(@class, "skuAttribute")]')
        if options:
            data = response.xpath('//script[contains(text(),"stockMatrix =")]/text()')[0].extract()
            data = data.replace('\n', '').replace('null', '"null"')
            data = re.search('stockMatrix = (.*?);', data, re.DOTALL)
            data = json.loads(data.group(1)) if data else []
            for i, variant in enumerate(data):
                sku = [elem for elem in variant if elem.startswith('sku')][0]
                sku_idx = variant.index(sku)
                product = Product(item)
                product['name'] = item['name'] + ' - ' + ' '.join(variant[:sku_idx]).title()
                product['identifier'] += '-' + sku
                product['price'] = extract_price(str(variant[sku_idx + 2]))
                if not('Available#Delivery' in variant[sku_idx + 1] or 'In stock#' in variant[sku_idx + 1] or 'Low stock#' in variant[sku_idx + 1]):
                    product['stock'] = 0

                image_code = response.xpath('//li[input[@value="'+variant[0]+'"]]/input[@class="colourImageUrl"]/@value').extract()
                if image_code:
                    image_url = 'http://media.very.co.uk/i/very/' + image_code[0]
                    product['image_url'] = image_url

                yield product
        else:
            yield item
