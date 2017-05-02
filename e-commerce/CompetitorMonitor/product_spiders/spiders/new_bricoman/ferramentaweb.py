import csv
import os
import re
import copy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar
from scrapy.utils.response import open_in_browser

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class FerramentaWebSpider(BaseSpider):
    name = 'newbricoman-ferramentaweb.com'
    allowed_domains = ('ferramentaweb.com',)
    start_urls = ('http://www.ferramentaweb.com/it/',)
    download_delay = 0

    def __init__(self, *args, **kwargs):
        super(FerramentaWebSpider, self).__init__(*args, **kwargs)
        self.ean_codes = {}
        self.model_codes = {}
        with open(os.path.join(HERE, 'bricoman_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('EAN', None):
                    self.ean_codes[row['EAN']] = row['Code']
                if row.get('model', None):
                    self.model_codes[row['model'].lower()] = row['EAN']

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        brands = hxs.select('//select[@id="manufacturer_list"]/option')[1:]
        for brand in brands:
            url = brand.select('@value').extract()[0]
            brand_name = brand.select('text()').extract()[0].strip()
            yield Request(url, callback=self.parse_list, meta={'brand': brand_name})

    def parse_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//div[@class="categTree"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_list, meta=response.meta)
        next_page = hxs.select('//ul[@class="pagination"]//a/@href').extract()
        if next_page:
            next_page = urljoin_rfc(base_url, next_page[0])
            yield Request(next_page, callback=self.parse_list, meta=response.meta)
        products = hxs.select('//ul[@id="product_list"]/li//h3/a/@href').extract()
        for url in products:
            url = urljoin_rfc(base_url, url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        name = hxs.select('//div[@id="pb-left-column"]/h1/text()').extract()
        if not name:
            return # Some weird template page
        loader.add_value('name', name[0].strip())
        category = u' > '.join(hxs.select(u'//div[@class="breadcrumb"]/a/text()').extract())
        loader.add_value('category', category)
        loader.add_xpath('identifier', '//input[@id="product_page_product_id"]/@value')
        loader.add_xpath('sku', '//p[@id="product_reference"]/span/text()')
        loader.add_value('brand', response.meta['brand'])
        try:
            price = hxs.select('//*[@id="our_price_display"]/text()')[0].extract().replace(u'.', u'').replace(u',', u'.').replace(' ', '')
        except IndexError:
            price = '0.00'
        loader.add_value('price', price)
        loader.add_xpath('image_url', '//img[@id="bigpic"]/@src')
        yield loader.load_item()
