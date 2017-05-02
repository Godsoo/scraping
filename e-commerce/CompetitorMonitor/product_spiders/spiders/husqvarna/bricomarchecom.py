# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import re
from product_spiders.utils import extract_price2uk

class BricomarcheSpider(BaseSpider):
    name = u'bricomarche.com'
    allowed_domains = ['bricomarche.com']
    start_urls = [
        u'http://produits.bricomarche.com/search?q=gardena',
        u'http://produits.bricomarche.com/search?q=flymo',
        u'http://produits.bricomarche.com/search?q=mc%20culloch',
        u'http://produits.bricomarche.com/search/?q=McCULLOCH',
    ]
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = response.css('.item a::attr(href)').extract()
        for url in items:
            search_str = response.xpath('//h1/em/text()').extract_first().capitalize()
            yield Request(urljoin(base_url, url), callback=self.parse_product, dont_filter=True, meta={'brand': search_str})

        pages = response.css('.pagi a::attr(href)').extract()
        for url in pages:
            yield Request(url, callback=self.parse)

        if not items:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                retry += 1
                new_meta = response.meta.copy()
                new_meta['retry'] = retry
                yield Request(response.url,
                              meta=new_meta,
                              callback=self.parse,
                              dont_filter=True)

    def parse_price(self, price):
        if price and isinstance(price, list):
            price = price.pop()
        else:
            return None
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+)\W.*', r'\1', price.strip().replace(u"\xa0", ""))
        except TypeError:
            return None
        if count:
            price = price.replace(",", ".").replace(" ", "")
            try:
                price = float(price)
            except ValueError:
                return None
            else:
                return price
        elif price.isdigit():
            return float(price)
        return None

    def get_sku_from_text(self, text):
        try:
            id, count = re.subn(r'[^0-9]*([0-9]*).*', r'\1', text)
        except TypeError:
            return ""
        if count:
            id = id.strip()
            try:
                int(id)
            except ValueError:
                return ""
            else:
                return id
        return ""

    def get_category_from_class(self, text):
        for item in text.split(" "):
            if item.startswith("category-"):
                return " ".join(item.split("-")[1:]).capitalize()
        return ""

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        try:
            name = response.css('.content-fiche-produit h1::text').extract_first().strip()
        except:
            retry = int(response.meta.get('retry', 0))
            if retry < 10:
                retry += 1
                new_meta = response.meta.copy()
                new_meta['retry'] = retry
                yield Request(response.url,
                              meta=new_meta,
                              callback=self.parse_product,
                              dont_filter=True)
            return

        category = response.css('#breadcrumb a::text').extract()
        if category:
            category = category[-2]
        else:
            category = ""

        sku = response.css('.content-fiche-produit p::text').re(u'Référence (\d+)')

        pid = response.css('.content-fiche-produit p::text').re(u'Ref (\d+)')

        price = response.css('.new-price ::text').extract_first()

        stock = bool(response.xpath('//p[contains(@class, "in-stock")]/text()').extract())
        if not stock:
            stock = 'DISPONIBLE' in ''.join(response.xpath('//p[contains(@class, "availability")]//text()').extract()).upper()

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            loader.add_css('image_url', '#image ::attr(src)')
            loader.add_value('price', extract_price2uk(price))
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', pid)
            loader.add_value('brand', response.meta.get("brand", ""))
            #loader.add_value('stock', int(stock))
            yield loader.load_item()
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))
