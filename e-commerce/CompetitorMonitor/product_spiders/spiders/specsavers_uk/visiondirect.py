# -*- coding: utf-8 -*-
"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4548
"""
import re
from scrapy import Spider, Request
from product_spiders.spiders.BeautifulSoup import BeautifulSoup

from product_spiders.items import ProductLoaderWithNameStrip, Product

from scrapy import log


class VisionDirectSpider(Spider):
    name = 'specsavers_uk-visiondirect'
    allowed_domains = ('visiondirect.co.uk', )

    start_urls = ['http://visiondirect.co.uk']

    def parse(self, response):
        soup = BeautifulSoup(response.body)

        categories = response.xpath('//div[contains(@class, "menu")]/@data-href').extract()
        categories += response.xpath('//ul[contains(@class, "menu")]//a/@href').extract()
        for cat_url in categories:
            yield Request(response.urljoin(cat_url), callback=self.parse_category)

        categories = soup.findAll('a', {'class': 'link'})
        for cat_url in categories:
            yield Request(response.urljoin(cat_url['href']), callback=self.parse_category)
        

    def parse_category(self, response):
        soup = BeautifulSoup(response.body)
        products = soup.findAll('a', {'class': 'products-list__item'})
        for product_url in products:
            yield Request(product_url['href'], callback=self.parse_product)

        identifier = re.search('"product_id":"([^"]*)"', response.body_as_unicode())
        if not products and identifier:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        soup = BeautifulSoup(response.body)

        # product list page
        products = soup.findAll('a', {'class': 'products-list__item'})
        if products:
            for r in self.parse_category(response):
                yield r
            return
        # discontinued product
        discontinued = response.xpath("//div[contains(@class, 'discontinued')]")
        if not discontinued:
            discontinued = 'Discontinued Product' in response.body
        if discontinued:
            return

        name = response.xpath("//h1[@itemprop='name']/text()").extract()
        if not name:
            name = soup.find('h1', {'itemprop': 'name'}).text
        price = re.findall(
            '"per_box_price_formated":"<span class=\\\\"price\\\\">\\\\u[\da-f]{4}([\d\.]*)<\\\\/span>",',
            response.body_as_unicode())[0]
        stock = None
        brand = response.xpath('//span[@itemprop="manufacturer"]/text()').re('by&nbsp;(.*)')
        if not brand:
            brand = soup.find('span', {'itemprop': 'manufacturer'}).text.split('by&nbsp;')[-1].strip()
        sku = re.search('"sku":"([^"]*)","product_id"', response.body_as_unicode()).group(1)
        identifier = re.search('"product_id":"([^"]*)"', response.body_as_unicode()).group(1)
        image_url = response.xpath("//img[@class='prod-image']/@src").extract()
        if not image_url:
            image_url = soup.find('img', {'itemprop': 'image'})['src']
        cats = []
        for el in response.xpath("//ul[@class='gl3-breadcrumbs']/li")[1:-1]:
            cats.append(''.join(el.xpath('.//text()').extract()).strip())

        shipping_cost = '2.98' if float(price) < 49 else '0'

        loader = ProductLoaderWithNameStrip(Product(), response=response)

        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('stock', stock)
        loader.add_value('url', response.url)
        loader.add_value('brand', brand)
        loader.add_value('sku', sku)
        loader.add_value('identifier', identifier)
        loader.add_value('image_url', image_url)
        loader.add_value('category', cats)
        loader.add_value('shipping_cost', shipping_cost)

        yield loader.load_item()
