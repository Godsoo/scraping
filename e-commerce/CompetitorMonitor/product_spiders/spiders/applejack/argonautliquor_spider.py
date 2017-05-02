# -*- coding: utf-8 -*-

import re
import os
import urllib
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

from product_spiders.spiders.BeautifulSoup import BeautifulSoup

from product_spiders.utils import extract_price

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class ArgonautLiquorSpider(BaseSpider):
    name = 'applejack-argonautliquor.com'
    allowed_domains = ['argonautliquor.com']
    start_urls = ('http://www.argonautliquor.com/sitemap.xml', )

    handle_httpstatus_list = [404, 302] 

    def parse(self, response):
        products = [url for url in re.findall('<loc>(.*)</loc>', response.body) if 'products' in url]
        for product in products:
            yield Request(product, callback=self.parse_product, meta={'dont_redirect': True})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        if response.status == 404 or response.status == 302:
            search_url = 'http://www.argonautliquor.com/results?term=' + response.url.split('products/')[-1]
            yield Request(search_url, callback=self.parse_product)
            return

        soup = BeautifulSoup(response.body, convertEntities=BeautifulSoup.HTML_ENTITIES)
        url = response.url
            
        image_url = soup.find('meta', attrs={'property': 'og:image'})
        image_url = image_url.get('content') if image_url and image_url.get('content') != 'http:' else ''

        try:
            brand = soup.find('h1', attrs={'class': 'itemTitle'}).find('span', attrs={'class': 'brand'}).text.strip()
        except AttributeError:
            brand = u''
        title = soup.find('h1', attrs={'class': 'itemTitle'}).find('span', attrs={'class': 'title'}).text.strip()
        try:
            vintage_age = soup.find('h1', attrs={'class': 'itemTitle'}).find('span', attrs={'class': 'vintageAge'}).text.strip()
        except AttributeError:
            vintage_age = u''


        dropdown = soup.find('select', attrs={'name': 'mv_order_item'})
        if not dropdown:
            multiple_prices = soup.find('div', attrs={'class': 'priceArea'}).findAll('td', attrs={'class': 'priceCell'})
            for option in multiple_prices:
                name = u'%s %s %s' % (brand, title, vintage_age)
                loader = ProductLoader(item=Product(), selector=option)
                loader.add_value('url', url)
                try:
                    price = option.find('p', attrs={'class': 'priceCellP salePriceP'}).find('span', attrs={'class': 'priceSale'}).text.strip()
                except AttributeError:
                    price = option.find('p', attrs={'class': 'priceCellP'}).find('span', attrs={'class': 'priceRetail'}).text.strip()
                try:
                    sku = option.find('p', attrs={'class': 'priceCellP itemid'}).text.strip()
                except AttributeError:
                    try:
                        sku = option.find('p', attrs={'class': 'priceCellP sku'}).text.strip()
                    except AttributeError:
                        try:
                            sku = option.find('p', attrs={'class': 'sku'}).text.strip()
                        except AttributeError:
                            try:
                                sku = option.find('span', attrs={'class': 'sku'}).text.strip()
                            except AttributeError:
                                sku = ''
                sku = sku.replace('SKU', '').strip()
                bottle_size = option.find('p', attrs={'class': 'priceCellP priceUnit'})

                if not bottle_size:
                    bottle_size = option.find(lambda tag: tag.name == 'span' and tag.get('class', '') == 'priceUnit' and tag.findParent('p', attrs={'class': 'priceCellP'}))
                if bottle_size:
                    name += u' %s' % bottle_size.text.strip()
                loader.add_value('name', name)
                loader.add_value('price', price)
                loader.add_value('brand', brand)
                loader.add_value('sku', sku)
                loader.add_value('identifier', sku)
                loader.add_value('image_url', image_url)
                if loader.get_output_value('price'):
                    yield loader.load_item()
        else:
            for option in dropdown.findAll('option'):
                name = u'%s %s %s' % (brand, title, vintage_age)
                option = re.search(r'(\$[\d\.]*) \(([^)]*)\) (.*)$', option.text).groups()
                price = option[0]
                name += u' %s' % option[1].strip()
                sku = option[2].replace('SKU', '').strip()
                loader = ProductLoader(item=Product(), selector=option)
                loader.add_value('url', url)
                loader.add_value('name', name)
                loader.add_value('price', price)
                loader.add_value('brand', brand)
                loader.add_value('sku', sku)
                loader.add_value('image_url', image_url)
                loader.add_value('identifier', sku)
                if loader.get_output_value('price'):
                    yield loader.load_item()
