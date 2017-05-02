# -*- coding: utf-8 -*-
"""
Customer: Specsavers NL
Website: http://www.q-lens.com
Extract all products

Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5107

"""

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request

from copy import deepcopy

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class Qlens(BaseSpider):
    name = "specsavers_nl-q-lens.com"
    allowed_domains = ["q-lens.com"]
    start_urls = ['http://www.q-lens.com']

    def parse(self, response):

        categories = response.xpath('//ul[@class="categories"]//a/@href').extract()
        categories += response.xpath('//ul[@class="productcategories"]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//div[@class="border_prods"]')
        if products:
            category = response.xpath('//div/h1[not(contains(text(), "Categories"))]/text()').extract() 
            category = category[0] if category else ''
            for product in products:
                url = product.xpath('.//span/a/@href').extract()[0]
                brand = product.xpath('.//tr[contains(.//strong/text(), "Manufacturer")]/td/strong/text()').extract()
                brand = brand[0] if brand else ''
                yield Request(response.urljoin(url), callback=self.parse_product, meta={'category': category, 'brand': brand})

    def parse_product(self, response):
        name = response.xpath('//h2/text()').extract()[0].strip()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', name)
        price = response.xpath('//span[@class="product_price_cost_total"]/text()').extract()
        price = extract_price(price[0]) if price else 0
        loader.add_value('price', price)
        image_url = response.xpath('//a[@class="prods_pic_bg"]/@href').extract()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url[0]))
        loader.add_value('brand', response.meta['brand'])
        loader.add_value('category', response.meta['category'])
        loader.add_value('url', response.url)
        identifier = response.xpath('//input[@name="products_id"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        sku = response.xpath('//div[@class="info"]/span/text()').re('Art.No.:(.*)')
        sku = sku[0].strip() if sku else ''
        loader.add_value('sku', sku)

        loader.add_value('shipping_cost', 5)

        item = loader.load_item()

        options = response.xpath('//table[@class="pricebox"]//tr')
        if options:
            for option in options:
                identifier = option.xpath('td/input/@value').extract()
                if identifier:
                    option_item = deepcopy(item)
                    option_item['name'] += ' ' + option.xpath('td[2]/text()').extract()[0].strip()
                    option_item['identifier'] += '-' + identifier[0]
                    price = option.xpath('td/b/text()').extract()[-1].strip()
                    option_item['price'] = extract_price(price)
                    yield option_item
        else:
            self.log('NO OPTIONS: ' + response.url)
            yield item
