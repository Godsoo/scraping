import csv
import os
import copy
import re
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class RedcoonSpider(BaseSpider):
    name = 'logitech_german-redcoon.de'
    allowed_domains = ['redcoon.de']

    start_urls = ('http://www.redcoon.de/search/?5000=&keywords=Logitech&sortfor=ctl_price',)

    map_products_csv = os.path.join(HERE, 'logitech_map_products.csv')
    map_price_field = 'map'
    map_join_on = [('sku', 'mpn'), ('sku', 'ean13')]

    def start_requests(self):

        for url in self.start_urls:
            yield Request(url)

        with open(HERE + '/logitech_extra_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['Redcoon'] != 'No Match':
                    yield Request(row['Redcoon'], callback=self.parse_product, meta={'sku':row['sku'], 'brand':row['brand']})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//span[@class="pagelinks"]/a[img[@alt=">"]]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//div[contains(@class,"product")]//h2/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        price = hxs.select(u'//p[@class="pd-price"]/img[not(contains(@src,"small"))]/@alt').extract()
        price_small = hxs.select(u'//p[@class="pd-price"]/img[contains(@src,"small")]/@alt').extract()
        price = ''.join(price)
        price_small = re.sub(u'[^\d]', u'', u''.join(price_small))
        price += price_small
        price = price.replace(',', '.')

        name = hxs.select(u'//h1[@class="pagetitle"]/span/text()').extract()
        name = map(lambda x: x.strip(), name)
        name = ' '.join(name)

        identifier = hxs.select('//span[@class="pd-id"]/text()').re('Nr\.: (.*)')

        image_url = hxs.select('//img[@id="showPic"]/@src').extract()

        category = hxs.select('//div[@class="breadcrumbs"]/a/text()').extract()

        stock = hxs.select('//span[@class="slo"]/text()').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier[0])

        sku = response.meta.get('sku', '')
        if sku:
            loader.add_value('sku', sku)
            loader.add_value('brand', response.meta.get('brand', ''))
        else:
            sku = hxs.select('//span[@id="cliplisterBox"]/@class').extract()
            if sku:
                loader.add_value('sku', sku[0])
            loader.add_value('brand', 'Logitech')

        loader.add_value('name', name)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_value('price', price)
        if category:
            loader.add_value('category', category[-1])

        if stock and ('1 woche' in stock[0].lower() or '3 monate' in stock[0].lower()):
            loader.add_value('stock', 0)
        yield loader.load_item()
