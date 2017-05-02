from __future__ import unicode_literals
from decimal import Decimal

import re
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu as extract_price


class RitualsSpider(BaseSpider):
    name = 'thebodyshop-rituals_fr'
    allowed_domains = ['eu.rituals.com']
    start_urls = [
        'https://eu.rituals.com/fr-fr/creme-pour-le-corps/mei-dao-3253.html#q=3253&start=1',
        'https://eu.rituals.com/fr-fr/baume/ginkgos-secret-9100.html?q=Ginkgo%27s%20Secret',
        'https://eu.rituals.com/fr-fr/gel-p%C3%A2te-de-douche/hammam-olive-secret-9815.html#start=3',
        'https://eu.rituals.com/fr-fr/rouge-%C3%A0-levres/lipstick--china-red-2519.html#start=2',
        'https://eu.rituals.com/fr-fr/correcteur/lighten-up-2-2572.html?q=Lighten%20Up%202',
        'https://eu.rituals.com/fr-fr/hydratation/24h-hydrating-gel-cream-6341.html?q=24h%20Hydrating%20Gel%20Cream',
        'https://eu.rituals.com/fr-fr/anti-%C3%A2ge/skin-energy-serum-6349.html?q=Skin%20Energy%20Serum',
        'https://eu.rituals.com/fr-fr/cremes/samurai-energize-9775.html?q=Samurai%20Energize',
    ]
    data_regex = re.compile('this\.products = ko.observableArray\((.*)\);')
    brand_regex = re.compile('brand: "(.*)",')

    def start_requests(self):
        yield Request('https://eu.rituals.com/on/demandware.store/Sites-EU-Site/fr_FR/Country-Select?switchpipeline=Home-Show&locale=fr_FR&country=FR', callback=self.parse_location)

    def parse_location(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)

        # sku and identifier
        loader.add_xpath('identifier', "//div[@class='sku']//span[@class='value']//text()")
        loader.add_xpath('sku', "//div[@class='sku']//span[@class='value']//text()")

        # name
        name = ''.join(hxs.select("//h1[@itemprop='name']/text()").extract())
        loader.add_value('name', name.strip())
        #price
        price = extract_price(
            ''.join(hxs.select('//span[@itemprop="price"]/text()').extract()))
        loader.add_value('price', price)
        #stock
        stock = 1
        if not price:
            stock = 0
        loader.add_value('stock', stock)
        #image_url
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        #brand
        # loader.add_xpath('brand', "//div[@class='primary-logo']//img/@alt")
        loader.add_value('brand', 'Rituals')
        #category
        category = hxs.select('//*[@id="add-to-cart"]/@data-category').extract()
        category = category[0] if category else ''
        loader.add_value('category', category)
        #shipping_cost
        loader.add_value('shipping_cost', Decimal(0))

        yield loader.load_item()
