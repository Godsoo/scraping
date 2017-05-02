"""
Rue Du Commerce spider
This spider is set to extract all Lego items and all dealers

It was created as a replacement for the carrefour.fr spider because the previous website now redirects
to this one.
"""

import re

from scrapy.spider import BaseSpider
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price_eu


class RueDuCommerceSpider(BaseSpider):
    name = 'legofrance-rueducommerce.fr'
    allowed_domains = ['rueducommerce.fr']
    start_urls = ('http://www.rueducommerce.fr/m/pl/malid:4820433;so:1;sc:2',)

    def parse(self, response):
        products = response.xpath('//a[span[@class="txtgris hover span-4 last txtm"]]/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//a[@class="txts txtgris gras pagination_pad"]/@href').extract()
        for url in next_page:
            yield Request(response.urljoin(url))

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        name = ' '.join(response.xpath('//h1//*/text()').extract())
        brand = response.xpath('//span[@itemprop="brand"]/a/span/text()').extract()
        price = response.xpath('//meta[@itemprop="price"]/@content').extract()
        price = price[0] if price else '0,00'
        categories = response.xpath('//nav[@class="breadcrumb"]//a/span/text()').extract()
        stock = response.xpath('//div[@class="productAvailability"]/div[contains(text(), "EN STOCK")]')
        image_url = response.xpath('//img[@id="photo"]/@src').extract()
        if image_url:
            image_url = 'http:' + image_url[0]
        sku = re.search('(\d{4,})', name)
        sku = sku.group(1) if sku else []
        if not sku:
            sku = response.xpath('//span[@itemprop="sku"]/text()').extract()
        identifier = response.xpath('//script[contains(text(),"mpid")]/text()').re('mpid\'\] = \'(.*)\';')
        loader.add_value('identifier', identifier)
        loader.add_value('name', name)
        loader.add_value('brand', brand)
        for category in categories:
            loader.add_value('category', category)
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_value('price', extract_price_eu(price))
        loader.add_value('image_url', image_url)
        if not stock:
            loader.add_value('stock', 0)
        item = loader.load_item()
        dealers = response.xpath('//tbody[@class="sellerList"]/tr')
        if not dealers:
            dealer_name = re.findall("\['merchantname'\] = '(.*)'", response.body)
            if dealer_name:
                item['identifier'] += u'-{}'.format(dealer_name[0].upper())
            yield item
            return
        for dealer in dealers:
            p = item.copy()
            dealer_name = dealer.xpath('td/text()')[0].extract()
            dealer_price = dealer.xpath('td[contains(@class, "price")]/text()').extract()
            p['identifier'] += u'-{}'.format(dealer_name.upper())
            p['price'] = extract_price_eu(dealer_price[0])
            yield p
