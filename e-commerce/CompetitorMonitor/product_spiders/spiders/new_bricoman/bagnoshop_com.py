# -*- coding: utf-8 -*-
import logging

import csv
import os.path
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class BagnoShopSpider(BaseSpider):
    name = 'newbricoman-bagnoshop.com'
    allowed_domains = ('bagnoshop.com', )
    start_urls = ('http://www.bagnoshop.com/', )

    def __init__(self, *args, **kwargs):
        super(BagnoShopSpider, self).__init__(*args, **kwargs)

        self.rows = []

        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.rows.append(row)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        categories = hxs.select("//td[@class='menu2']//a/@href").extract()

        for category_url in categories:
            url = urljoin_rfc(get_base_url(response), category_url)

            r = Request(url, callback=self.parse_products_list)
            yield r

    def _check_dispo(self, response):
        if 'non disponibile' in response.body.lower():
            logging.error("ASD. Found dispon: %s" % response.url)

    def parse_products_list(self, response):
        self._check_dispo(response)
        hxs = HtmlXPathSelector(response)

        sub_cats = hxs.select("//div[@id='contenuto']/div[1]/div[1]//div[@class='content']//a/@href").extract()
        for category_url in sub_cats:
            url = urljoin_rfc(get_base_url(response), category_url)

            r = Request(url, callback=self.parse_products_list)
            yield r

        pages = hxs.select("//div[@class='pgNumContainer']//a/@href").extract()
        for page_url in pages:
            url = urljoin_rfc(get_base_url(response), page_url)

            r = Request(url, callback=self.parse_products_list)
            yield r

        category = hxs.select("//tr[@id='nav0_ROW1']/td[last()]//text()").extract()[0]
        products = hxs.select("//div[contains(@class, 'cat-item')]")
        for p in products:
            name = p.select("div[@class='product_description']/div[@class='catprod_name']/a/text()").extract()[0]
            url = p.select("div[@class='product_description']/div[@class='catprod_name']/a/@href").extract()[0]
            url = urljoin_rfc(get_base_url(response), url)
            brand = p.select("div[@class='product_description']/div[@class='catprod_name']/div[@class='catprod_azienda']/text()").extract()
            if brand:
                brand = brand[0].strip()
            else:
                brand = ''
            price = p.select("div[@class='product_description']/div[@class='cat_of_products_price item-price']/span[@class='cat-price']/text()").extract()[0]
            price = price.replace(".", "").replace(",", ".")

            image_url = p.select("a/img/@src").extract()
            if image_url:
                image_url = image_url[0]
                image_url = urljoin_rfc(get_base_url(response), image_url)
            else:
                image_url = ''

            sku = ""
            identifier = re.search(r'bagnoshop.com\/(.*).html', url).group(1)

            stock = None

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_value('category', category)
            loader.add_value('brand', brand)
            loader.add_value('image_url', image_url)
            loader.add_value('sku', sku)
            loader.add_value('identifier', identifier)
            loader.add_value('stock', stock)
            loader.add_value('price', price)

            yield loader.load_item()

