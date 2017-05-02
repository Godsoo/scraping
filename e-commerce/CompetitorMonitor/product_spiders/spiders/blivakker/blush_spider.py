# -*- coding: utf-8 -*-
"""
Customer: Blivakker
Website: http://www.blush.no
Extract all products on site

Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4639-blivakker-|-blush-no-|-new-spider/details#

"""

import json
from scrapy import Spider, Request
from product_spiders.utils import extract_price_eu
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class BlushSpider(Spider):
    name = 'blivakker-blush.no'
    allowed_domains = ['blush.no']
    start_urls = ['https://www.blush.no/brand']

    def parse(self, response):
        brands = response.xpath('//div[contains(@class, "brands-list")]//a[@class="btn-link"]/@href').extract()
        for brand in brands:
            url = response.urljoin(brand)
            if 'hits=9999' not in brand:
                url = url + '&hits=9999'
            yield Request(url)

        categories = response.xpath('//a[@class="nav-bar-list-item-link"]/@href').extract()
        categories += response.xpath('//ul[@class="category-list"]//a/@href').extract()
        categories += response.xpath('//div[@class="responsive-content-wrapper"]//a[not(contains(@href, "/product/")) and @href!="#" and @href!="" and not(contains(@data-bind, "addProductLink"))]/@href').extract()
        for category in categories:
            url = response.urljoin(category)
            if 'hits=9999' not in category and '/product/' not in category:
                url = url  +'&hits=9999'
            yield Request(url)

        products = response.xpath('//a[contains(@class, "product-link")]/@href').extract()
        for product in products:
            yield Request(response.urljoin(product), callback=self.parse_product)

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        sku = response.xpath('//span[@itemprop="sku"]/text()').extract()[0]
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)

        loader.add_xpath('brand', '//span[@itemprop="manufacturer"]/text()')

        name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0].strip()
        desc = ''.join(response.xpath('//h2[@itemprop="description"]/text()').extract()).strip()
        if desc:
            name = name + ' ' + desc
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        price = extract_price(response.xpath('//*[@itemprop="price"]/@content').extract_first())
        if price < 295:
            shipping_cost = 29
        else:
            shipping_cost = 0
        price_before = response.css('.product-main-info .product-price-before::text').extract_first()
        if price_before:
            sales_price = price
            price = extract_price_eu(price_before)
        else:
            sales_price = None
        loader.add_value('price', price)

        image_url = response.xpath('//div[@class="swiper-slide"]/img/@data-src').extract()
        image_url = response.urljoin(image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)

        breadcrumbs = response.css('nav.breadcrumbs::attr(data-initobject)').extract_first()
        breadcrumbs = json.loads(breadcrumbs)['model']['links'][-3:]
        categories = [category['title'] for category in breadcrumbs]
        if 'Forsiden' in categories:
            categories.remove('Forsiden')
        loader.add_value('category', categories)

        loader.add_value('shipping_cost', shipping_cost)

        item = loader.load_item()
        if sales_price:
            item['metadata'] = {'SalesPrice': sales_price}

        yield item
