# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from scrapy.http import Request
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from urlparse import urljoin as urljoin_rfc


class Rituals(BaseSpider):
    name = u'thebodyshop-rituals.com'
    allowed_domains = ['eu.rituals.com', 'uk.rituals.com']
    start_urls = [
        'https://uk.rituals.com/en-gb/body-moisturisers/mei-dao-3253.html#q=3253&start=1',
        'https://uk.rituals.com/en-gb/balm/ginkgos-secret-9100.html?q=Ginkgo%27s%20Secret',
        'https://uk.rituals.com/en-gb/shower-gel-paste/hammam-olive-secret-9815.html#start=3',
        'https://uk.rituals.com/en-gb/lipstick/lipstick--china-red-2519.html#start=2',
        'https://uk.rituals.com/en-gb/concealers/lighten-up-2-2572.html?q=Lighten%20Up%202',
        'https://uk.rituals.com/en-gb/hydrating/24h-hydrating-gel-cream-6341.html?q=24h%20Hydrating%20Gel%20Cream',
        'https://uk.rituals.com/en-gb/anti-aging/skin-energy-serum-6349.html?q=Skin%20Energy%20Serum',
        'https://uk.rituals.com/en-gb/creams/samurai-energize-9775.html?q=Samurai%20Energize'
    ]

    def start_requests(self):
        yield Request('https://eu.rituals.com/on/demandware.store/Sites-UK-Site/en_GB/Country-Select?switchpipeline=Home-Show&locale=en_GB&country=GB', callback=self.parse_location)

    def parse_location(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        category = hxs.select('//*[@id="add-to-cart"]/@data-category').extract()
        category = category[0] if category else ''
        # brand = hxs.select('//div[@class="primary-logo"]//span/text()').extract()
        # brand = brand[0] if brand else ''
        name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        price = hxs.select('//span[@class="price-sales "]/text()').extract()[0]
        price = extract_price(price)
        identifier = hxs.select('//*[@id="pid"]/@value').extract()[0].strip()

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('identifier', identifier)
        product_loader.add_value('name', name)
        if image_url:
            product_loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        product_loader.add_value('sku', identifier)
        product_loader.add_value('price', price)
        product_loader.add_value('brand', 'Rituals')
        product_loader.add_value('url', response.url)
        product_loader.add_value('category', category)
        # product_loader.add_value('brand', brand)
        product = product_loader.load_item()
        yield product
