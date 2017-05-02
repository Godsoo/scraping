# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector, XmlXPathSelector
from scrapy.contrib.loader import ItemLoader
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy.http import Request, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
import re, time

from selenium import webdriver

from product_spiders.base_spiders.primary_spider import PrimarySpider


class TredzSpider(BaseSpider):
    name = "tweekscycles-tredz.co.uk"
    allowed_domains = ['tredz.co.uk']
    start_urls = ["http://www.tredz.co.uk"]

    base_url = "http://www.tredz.co.uk"


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@class="body-wrapper"]/ul/li//a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        items = hxs.select('//div[@data-productid]/a/@href').extract()
        for url in items:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_item)

        next_page = hxs.select('//a[span[@class="pagination-next"]]/@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)

    def parse_item(self, response):
        '''
                skuArray.push({
                    productexternalid: 72833,
                    colour: 'Light Grey/Grey',
                    size: '49',
                    skuNopId: 91684,
                    skuId: 227272,
                    price: '£90.00',
                    priceAsDecimal: 90.0000,
                    stockquantity: 0,
                    preorder: true,
                    outofstock: true,
                    issubscribed: false,
                    availableDate: 'Due in 02/07/2015'
                    });
        '''
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products_data = []
        collect_product = False
        for i, l in enumerate(response.body.split('\n')):
            if 'skuArray.push({' in l:
                collect_product = True
                current_product = {}
                continue
            if '});' in l and collect_product:
                collect_product = False
                products_data.append(current_product)
                continue
            if collect_product:
                attr_data = [a.strip() for a in l.split(':')]
                current_product[attr_data[0]] = eval(attr_data[1].replace('false', 'False').replace('true', 'True'))
                if isinstance(current_product[attr_data[0]], tuple):
                    current_product[attr_data[0]] = current_product[attr_data[0]][0]

        main_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0].strip()
        categories = hxs.select('//div[@id="breadcrumb"]//span[@itemprop="title"]/text()').extract()[1:]

        for p in products_data:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_xpath('image_url', '//img[@itemprop="image"]/@src', lambda a: urljoin_rfc(base_url, a[0]) if a else '')
            loader.add_value('identifier', p['skuId'])
            loader.add_value('sku', p['productexternalid'])
            loader.add_value('price', p['priceAsDecimal'])
            loader.add_value('stock', p['stockquantity'])
            loader.add_value('category', categories)
            loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
            loader.add_value('url', response.url)
            loader.add_value('name', main_name + ' - ' + p['colour'] + ' - ' + p['size'])

            yield loader.load_item()
