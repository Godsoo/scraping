# -*- coding: utf-8 -*-

try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider

from scrapy.http import Request
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price


class SXChangeThomannSpider(BaseSpider):
    name = u'studioxchange-thomann.de'
    allowed_domains = ['thomann.de']
    start_urls = [
        u'http://www.thomann.de/gb/index.html',
    ]

    headers = {
        'User-agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/33.0.1750.154 Safari/537.36'
    }

    def parse(self, response):
        # categories
        urls = response.xpath('//div[contains(@class, "lr-navi-categories")]/ul/li/a/@href').extract()
        for url in urls:
            yield Request(response.urljoin(url),
                          callback=self.parse_subcategories)

    def parse_subcategories(self, response):
        # subcategories
        urls = response.xpath('//li[contains(@class, "lr-cat-subcategories")]/a/@href').extract()
        for url in urls:
            yield Request(response.urljoin(url),
                          callback=self.parse_subcategories)
        # pagination
        urls = response.xpath('//div[@id="resultPageNavigation"]//div//a/@href').extract()
        for url in urls:
            yield Request(response.urljoin(url),
                          callback=self.parse_subcategories)
        # products
        products = response.xpath('//div[contains(@class, "search-entry")]')
        for product in products:
            brand = product.xpath('.//span[@class="manufacturerName"]/text()').extract()
            brand = brand[0] if brand else ''
            url = product.xpath('.//a/@href').extract()[0]
            yield Request(response.urljoin(url),
                          callback=self.parse_product,
                          meta={'brand': brand})

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        name = response.xpath('//h1[@itemprop="name"]/text()').extract()
        if name:
            name = name[0].strip()
        else:
            retry_count = response.meta.get('retry_count', 0)
            if retry_count<3:
                yield Request(response.url, dont_filter=True, callback=self.parse_product, meta={'retry_count':retry_count+1})
            else:
                self.log('Product without name: ' + response.url)
                return

        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('brand', response.meta.get('brand'))
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract()
        if image_url:
            image_url = response.urljoin(image_url[0])
            loader.add_value('image_url', image_url)
        available = ''.join(response.xpath('//div[@itemprop="offers"]//div[contains(@class,"tr-prod-availability")]//text()')
                            .extract())\
                      .strip().upper()
        if available:
            if 'AVAILABLE IMMEDIATELY' not in available.upper():
                loader.add_value('stock', 0)
        price = response.xpath('//*[@itemprop="price"]/following-sibling::span/text()').extract()
        price = extract_price(price[0]) if price else 0
        loader.add_value('price', price)
        category = response.xpath('//ul[@class="tr-sidebar-categories-main"]/li/a/text()').extract()
        if category:
            loader.add_value('category', category[0])
        sku = response.xpath('//input[@name="ar"]/@value').extract()
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)
        loader.add_value('identifier', sku)
        if int(price) <= 165:
            loader.add_value('shipping_cost', 8.3)
        yield loader.load_item()
