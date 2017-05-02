# -*- coding: utf-8 -*-
import os
import json
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class Home24Spider(BaseSpider):
    name = 'made_fr-home24.fr'
    allowed_domains = ['home24.fr']
    start_urls = ['http://www.home24.fr/meubles/?order=name_asc',
                  'http://www.home24.fr/luminaires/?order=name_asc',
                  'http://www.home24.fr/accessoires/?order=name_asc']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = response.xpath('//div[contains(@class,"pagination")]/a[@rel="next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = response.xpath('//div[@class="article-tile__wrap"]')
        for product in products:
            url = product.select('.//a/@href')[0].extract()
            image_url = product.select('.//div[@class="article-tile__images"]/div/img/@data-echo')[0].extract()
            price = product.select('.//span[contains(@class,"article__price ")]/text()')[0].extract()
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product, meta={'image_url': image_url, 'price': price})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in response.xpath('//meta[@itemprop="isSimilarTo"]/@content').extract():
            yield Request(url, meta=response.meta, callback=self.parse_product)
            yield Request(url.replace('undefinedundefined', '.fr/'), callback=self.parse_product)

        sku = response.xpath('//*[@itemprop="sku"]/@content').extract()
        name = response.xpath('//script/text()').re('"productName": "(.+)"')
        brand = response.xpath('//script/text()').re('"productBrand": "(.+)"')
        categories = response.css('.breadcrumbs').xpath('.//span[@itemprop="name"]/text()').extract()[1:]

        options = response.css('.mvc-configurator__options')
        data = re.findall('window.__INITIAL_STATE__ = (.+)<', response.body)[0]
        data = json.loads(data)

        if options:
            for option in data['children'].itervalues():

                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('identifier', option['trackingData']['sku'])
                loader.add_value('sku', sku)
                loader.add_value('url', response.url)
                loader.add_value('name', option['trackingData']['name'])
                loader.add_value('image_url', response.urljoin(option['images'][0]['big']['src']))
                loader.add_value('price', option['trackingData']['price'])
                loader.add_value('brand', brand)
                for category in categories:
                    loader.add_value('category', category)

                yield loader.load_item()
        else:
            #name = response.xpath('//div[@itemprop="name"]/h1/text()').extract()
            sub_name = response.xpath('//div[@itemprop="name"]/span/text()').extract()
            name = name[0].strip() if name else ''
            loader = ProductLoader(item=Product(), selector=hxs)
            identifier = re.sub('-C$', '', sku[0])
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('name', name)
            loader.add_xpath('price', '//script/text()', re='"productPrice": (.+),')
            loader.add_value('brand', brand)
            loader.add_value('image_url', response.urljoin(data['children'].values()[0]['images'][0]['big']['src']))
            for category in categories:
                loader.add_value('category', category)
            loader.add_value('stock', 0)

            yield loader.load_item()
