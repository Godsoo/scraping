import csv
import os
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from decimal import Decimal
from utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class HPTStoreSpider(BaseSpider):
    name = 'newbricoman-hptstore.com'
    allowed_domains = ('hptstore.com',)
    start_urls = ('http://www.hptstore.com',)

    def __init__(self, *args, **kwargs):
        super(HPTStoreSpider, self).__init__(*args, **kwargs)
        self.ean_codes = {}
        self.model_codes = {}
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('EAN', None):
                    self.ean_codes[row['EAN']] = row['Code']
                if row.get('model', None):
                    self.model_codes[unicode(row['model'].lower(), errors='ignore')] = row['EAN']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select(u'//a[@class="level-top"]/@href').extract()
        for url in categories:
            url = urljoin_rfc(base_url, url)
            yield Request(url)
        next_page = hxs.select(u'//a[@class="next i-next"]/@href').extract()
        if next_page:
            url = urljoin_rfc(base_url, next_page[0])
            yield Request(url)
        products = hxs.select(u'//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        category = hxs.select(u'//div[@class="breadcrumbs"]/ul/li//text()').extract()
        category = u' > '.join([x.strip() for x in category if len(x.strip()) > 1])
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        name = hxs.select(u'//div[contains(@class,"product-name")]/h1/text()')[0].extract().strip()
        loader.add_value('name', name)
        loader.add_value('category', category)
        identifier = hxs.select(u'//div[@class="product-shop"]').re(u'Codice: (.*?)<')[0].strip()
        loader.add_value('identifier', identifier)
        found = False
        if identifier in self.ean_codes:
            loader.add_value('sku', identifier)  # self.ean_codes[identifier])
            found = True
        else:
            for model in self.model_codes.keys():
                if len(model) > 3 and model in name.lower():
                    loader.add_value('sku', self.model_codes[model])
                    found = True
                    break
        if not found:
            loader.add_value('sku', '')
        price = hxs.select(u'//span[@class="price"]/text()').re(u'\u20ac(.*)')[0].strip().replace(u'.', u'').replace(u',', u'.')
        loader.add_value('price', price)
        image_url = hxs.select(u'//a[@class="MagicZoomPlus"]/img/@src').extract()
        if image_url:
            image_url = urljoin_rfc(base_url, image_url[0])
            loader.add_value('image_url', image_url)

        price = extract_price(price)

        if price < Decimal(100):
            loader.add_value('shipping_cost', '11.00')

        yield loader.load_item()
