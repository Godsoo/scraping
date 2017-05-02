# -*- coding: utf-8 -*-

import json
import urllib
import re
import collections
import time
from decimal import Decimal

from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import file_uri_to_path, urljoin_rfc
from scrapy import log

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader
)

from string import join


class debonix_spider(BigSiteMethodSpider):
    name = 'debonix.fr'
    inserted_products = set([])
    allowed_domains = ['debonix.fr']
    start_urls = ('http://www.debonix.fr/outillage-mesure.html',
                  'http://www.debonix.fr/jardin-piscine-exterieur.html',
                  'http://www.debonix.fr/levage-manutention.html',
                  'http://www.debonix.fr/electricite-domotique.html',
                  'http://www.debonix.fr/chauffage-plomberie-sanitaire.html',
                  'http://www.debonix.fr/hygiene-protection.html',
                  'http://www.debonix.fr/quincaillerie.html',
                  'http://www.debonix.fr/soudage-decoupage-plasma.html',
                  'http://www.debonix.fr/quincaillerie.html',
                  'http://www.debonix.fr/maison-decoration.html'
                  )

    website_id = 39065
    errors = []
    full_crawl_day = 2
    max_ocr_retries = 3

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        if not isinstance(response, HtmlResponse):
            return

        # categories
        cats = hxs.select(
                '//ol[@class="nav-primary"]//a/@href'
                ).extract()

        # Outilmania
        cats += hxs.select('//dl[@id="narrow-by-list2"]'
                           '//a/@href').extract()

        for cat in cats:
            if '?' not in cat:
                cat += '?dir=asc&order=price'
            else:
                cat += '&dir=asc&order=price'
            yield Request(url=cat, callback=self.parse_full)

        # next page
        next_page = hxs.select(
                '//a[@class="next i-next"]/@href'
                ).extract()
        if next_page:
            yield Request(url=next_page[0], callback=self.parse_full)

        # products
        for product in self.parse_products(response):
            yield product

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="product-info"]')
        for p in products:
            try:
                url = p.select('.//h2[@class="product-name"]/a/@href').extract()[0].strip()
            except:
                continue

            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        options = response.xpath('//*[contains(@class, "config-product-option")]'
                             '//option[contains(@class, "single-option")]/@value').extract()

        if options:
            for option in options:
                param = '?conf=%(option)s' % ({'option': option})
                yield Request(urljoin_rfc(response.url,
                                          file_uri_to_path(response.url) + param),
                              callback=self.parse_product)

        dinamic_name = join(hxs.select('//*[@class="dynamic-name"]/text()')
                            .extract())
        stock = hxs.select('//div[@id="product_type_data"]/div[@class="availability"]/span[contains(@class, "spr-icon-dispo-big-10") or contains(@class, "spr-icon-dispo-big-50")]')
        categories = hxs.select('//div[@class="breadcrumbs"]//a/text()')[1:].extract()
        if dinamic_name:
            name = dinamic_name
        else:
            name = join(hxs.select('//li[@class="home"]//strong/text()')
                        .extract())

        if not name:
            name = join(hxs.select('//div[@id="product_description"]'
                                   '//div[@class="etiquette-title"]/span'
                                   '/span/text()').extract())
        if not name:
            name = join(hxs.select('//li[@class="home"]'
                                   '//*[@class="store-main-color"]/text()')
                        .extract())

        if not name:
            name = join(hxs.select('//div[@class="product-name"]//h1/text()').extract())

        sku = join(hxs.select('//div[@class="sku-product"]/span[@class="sku"]/text()')
                   .extract()).strip()
        if not 'outilmania.fr' in response.url:
            price_url = hxs.select('//div[@class="price-box"]'
                                   '//img/@src').extract()

            if len(price_url) > 1:
                price_url = hxs.select('//div[@class="price-box"]'
                                       '//*[contains(@class, "special-price") '
                                       'or contains(@class, "normal-price")]'
                                       '//img/@src').extract()
                
            price_no_vat = response.xpath('//script/text()').re('"productPrice":"(.+?)"')
            if price_no_vat:
                price = (Decimal(price_no_vat[0]) * Decimal('1.2')).quantize(Decimal('0.01'))
            else:
                if price_url:
                    params = {
                        'url': price_url[0],
                        'resize': '200',
                        'mode': '',
                        'blur':'1',
                        'format':'float'}

                    # doing OCR decoding in 3 different modes to increase accuracy
                    prices = []
                    price = '0.00'
                    attempt = 0
                    while len(prices) == 0 and attempt < self.max_ocr_retries:
                        attempt += 1
                        self.log('OCR: {}, attempt {}'.format(price_url[0], attempt))
                        for mode in ('6', '7', '8'):
                            params_copy = params.copy()
                            params_copy['mode'] = mode
                            params_copy_encoded = urllib.urlencode(params_copy)
                            ocr_service_url = "http://148.251.79.44/ocr/get_price_from_image?%s" % params_copy_encoded
                            self.log('>>> GET PRICE => %s' % ocr_service_url)
                            f = urllib.urlopen(ocr_service_url)
                            jdata = json.loads(f.read())
                            self.log(str(jdata))
                            if len(jdata['price']) > 0:
                                prices.append(jdata['price'])
                    try:
                        price = self._select_price(prices)
                    except:
                        # self.errors.append("Price error, posibly ocr error on " + response.url)
                        pass

                    price = price.encode('utf-8')
                    price = price.replace(" ", "").replace(",", ".")
                    log.msg(str(price), log.DEBUG)
                else:
                    return
        else:
            faction = hxs.select('//form[@id="product_addtocart_form"]/@action').extract()[0]
            image_url = hxs.select('//div[@class="product-image-gallery"]/img[@id="image-main"]/@src').extract()
            yield Request(faction,
                          meta={'name': name,
                                'url': response.url,
                                'sku': sku,
                                'identifier': sku,
                                'image_url': image_url,
                                'categories': categories},
                          callback=self.parse_outilmania_price,
                          dont_filter=True)
            return
        if sku and price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('name', name)
            loader.add_value('url', response.url)
            loader.add_value('price', price)
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)
            loader.add_xpath('image_url', '//div[@class="product-image-gallery"]/img[@id="image-main"]/@src')
            loader.add_value('stock', 1)
            for category in categories:
                loader.add_value('category', category)
            yield loader.load_item()

    def parse_outilmania_price(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = response.meta.get('name')
        url = response.meta.get('url')
        sku = response.meta.get('sku')
        categories = response.meta.get('categories')
        identifier = response.meta.get('identifier')
        image_url = response.meta.get('image_url')

        price_url = hxs.select(u'//td[@class="product"]/span[@class="sku" and text()="Référence : ' +
                               sku + '"]/../following-sibling::td[@class="prix"]/span/img/@src').extract()[-1]

        params = {
                'url': price_url,
                'resize': '',
                'mode': '',
                'blur':'1',
                'format':'float'}

        # doing OCR decoding in 3 different modes to increase accuracy
        prices = []
        attempt = 0
        while len(prices) == 0 and attempt < self.max_ocr_retries:
            attempt += 1
            self.log('OCR: {}, attempt {}'.format(price_url, attempt))
            for size in ('200', '250', '300'):
                for mode in ('6', '7', '8'):
                    params_copy = params.copy()
                    params_copy['mode'] = mode
                    params_copy['resize'] = size
                    params_copy_encoded = urllib.urlencode(params_copy)
                    ocr_service_url = "http://148.251.79.44/ocr/get_price_from_image?%s" % params_copy_encoded
                    # self.log('>>> GET PRICE => %s' % ocr_service_url)
                    f = urllib.urlopen(ocr_service_url)
                    jdata = json.loads(f.read())
                    # log.msg(str(jdata), log.DEBUG)
                    if len(jdata['price']) > 0:
                        prices.append(jdata['price'])

        price = self._select_price(prices)

        price = price.encode('utf-8')
        price = price.replace(" ", "").replace(",", ".")
        if '.' not in price:
            price = price[:-2] + '.' + price[-2:]
        log.msg(str(price), log.DEBUG)

        if sku and price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_value('price', price)
            loader.add_value('sku', sku)
            loader.add_value('identifier', identifier)
            loader.add_value('image_url', image_url)
            loader.add_value('stock', 1)
            for category in categories:
                loader.add_value('category', category)
            yield loader.load_item()

    def _select_price(self, prices):
        prices = [p for p in prices if len(p) > 0]
        prices = map(lambda p: p[:-2] + '.' + p[-2:] if '.' not in p else p, prices)
        # counting the most frequent price
        x = collections.Counter(prices)
        price, count = x.most_common()[0]
        for p, c in x.most_common():
            if c == count and float(p) > float(price):
                price = p
        # if there's no most common pick the one with decimal and 2 digits after it
        if count < 2 or not re.search("\d*\.\d{2}", price):
            for pr in prices:
                if re.search("\d*\.\d{2}", pr):
                    price = pr
                    break
        return price
