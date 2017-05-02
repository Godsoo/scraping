# -*- coding: utf-8 -*-

import os
import json
from decimal import Decimal

from scrapy import Request, Selector
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.item import Item, Field
from product_spiders.utils import extract_price
from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from product_spiders.lib.schema import SpiderSchema


HERE = os.path.abspath(os.path.dirname(__file__))


class MetaData(Item):
    Promotions = Field()


class VictoriaPlumSpider(CrawlSpider):
    name = 'bathempire-victoriaplum.com'
    allowed_domains = ['victoriaplum.com']
    start_urls = ['https://victoriaplum.com']
    
    categories = LinkExtractor(allow=('/category/', '/browse/'))
    products = LinkExtractor(allow='/product/')
    
    rules = (
        Rule(categories),
        Rule(products, callback='parse_product')
        )

    def parse_product(self, response):
        schema = SpiderSchema(response)
        pdata = schema.get_product()

        sku = response.xpath('//meta[@itemprop="productId"]/@content').extract()
        if not sku:
            self.log('Product without identifier: ' + response.url)
            return

        name = pdata['name']
        price = extract_price(pdata['offers']['properties']['price'])

        brand = response.xpath('//tr[th[contains(text(), "Range Name")]]/td/text()').extract()
        brand = brand[0].strip() if brand else ''
        categories = response.xpath('//a[@class="breadcrumb__link"]/span/text()').extract()[1:]

        l = ProductLoader(item=Product(), response=response)

        image_url = response.xpath('//div[contains(@class, "product-slider__element")]//img[@itemprop="image"]/@src').extract()
        if not image_url:
            image_url = response.xpath('//div[contains(@class, "product-slider__carousel")]//img[@itemprop="image"]/@src').extract()
        image_url = image_url[0] if image_url else ''

        l.add_value('image_url', image_url)
        l.add_value('url', response.url)
        l.add_value('name', name)
        discount_percentage = response.xpath('//span[@class="voucher-banner__title"]/text()').re('(\d+)%')
        if discount_percentage:
            price = price - ((int(discount_percentage[0]) * price) / Decimal(100))

        l.add_value('price', price)
        l.add_value('brand', brand)
        l.add_value('category', categories)

        sku = sku[0]
        l.add_value('sku', sku)

        l.add_value('identifier', sku)

        out_of_stock = response.xpath('//i[contains(@class, "stock-indicator__status--inactive")]')
        if out_of_stock:
            l.add_value('stock', 0)

        item = l.load_item()

        promotions = response.xpath('//span[contains(@class, "price--type-was")]//text()').extract()
        if not promotions:
            promotions = response.xpath('//div[contains(@class, "price--type-was")]//span[@class="text--strikethrough"]//text()').extract()

        metadata = MetaData()
        metadata['Promotions'] = ' '.join(map(lambda x: x.strip(), promotions)).strip() if promotions else ''
        item['metadata'] = metadata
        
        options = response.css('.variant__selector select option')
        if not options:
            yield item
            return
        
        for option in options:
            sku = option.xpath('@data-sku').extract_first()
            token = response.xpath('//@data-token').extract_first()
            headers = {
                'Content-Length': 0,
                'X-CSRF-Token': token,
                'X-Requested-With': 'XMLHttpRequest'
                    }
            yield Request('https://victoriaplum.com/api/v1/variant/%s/details' %sku, self.parse_option, method='POST', headers=headers, meta={'item': Product(item)})
            
    def parse_option(self, response):
        item = response.meta['item']
        data = json.loads(response.body)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value(None, item)
        loader.replace_value('identifier', data['sku'])
        loader.replace_value('sku', data['sku'])
        
        selector = Selector(text=data['productPrices'])
        price = selector.css('.price-group').xpath('span/span//text()').extract()
        loader.replace_value('price', ''.join(price))
        was_price = selector.css('.price-group p span.text--strikethrough ::text').extract()
        loader.replace_value('url', data['url'])
        
        selector = Selector(text=data['stock'])
        out_of_stock = selector.css('.stock-indicator__status--inactive')
        loader.replace_value('stock', int(not out_of_stock))
        
        selector = Selector(text=data['navigationTitle'])
        loader.add_value('name', selector.css('.sub-title::text').extract_first())
        item = loader.load_item()
        
        was_price = extract_price(''.join(was_price))
        metadata = MetaData()
        metadata['Promotions'] = was_price if was_price else ''
        item['metadata'] = metadata
        yield item
        
