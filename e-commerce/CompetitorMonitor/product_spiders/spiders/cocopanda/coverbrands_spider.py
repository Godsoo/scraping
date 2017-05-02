import os
import csv

from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

HERE = os.path.abspath(os.path.dirname(__file__))

class CoverBrandsSpider(BaseSpider):
    name = 'cocopanda-coverbrands.no'
    allowed_domains = ['coverbrands.no']
    start_urls = ['http://www.coverbrands.no/']

    user_agent = 'Googlebot/2.1 (+http://www.google.com/bot.html)'

    def parse(self, response):
        with open(os.path.join(HERE, 'coverbrands.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                p = Product()
                for k, value in row.items():
                    if k == 'price':
                        p[k] = Decimal(value or 0)
                    else:
                        p[k] = value

                yield p

    '''
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@id="nav"]/li/a/@href').extract()
        for url in categories:
            if 'limit=all' not in url:
                url = url + '?limit=all' if not '?' in url else url + '&limit=all'
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        meta = {'category': hxs.select('//ul[@id="nav"]/li[contains(@class, "active")]/a/span/text()').extract()[0].strip()}
        urls = hxs.select('//ul/li[contains(@class, "item")]//h2[@class="fp-article-title"]/a/@href').extract()
        for url in urls:
            yield Request(url, self.parse_product, meta=meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        brand = hxs.select('//div[@class="product-shop"]//div[@class="product-name"]/h1/text()').extract()
        if brand:
            product_loader.add_value('brand', brand[0].strip())
        identifier = hxs.select('//div[@class="no-display"]/input[@name="product"]/@value').extract()[0].strip()
        product_loader.add_xpath('identifier', identifier)
        product_loader.add_xpath('sku', identifier)
        product_loader.add_xpath('name', '//div[@class="product-shop"]//h3[@itemprop="name"]/text()')
        price = hxs.select('//span[@id="product-price-%s"]/text()' % identifier).extract()[0].strip().replace(',', '.')
        if not price:
            price = hxs.select('//span[@id="product-price-%s"]/span/text()' % identifier).extract()[0].strip().replace(',', '.')
        if not price:
            self.log('WARNING: NON PRICE!')
        product_loader.add_value('price', price)
        product_loader.add_value('category', response.meta['category'])
        product_loader.add_xpath('image_url', '//a[@id="image-zoom"]/img/@src')
        product_loader.add_value('url', response.url)

        yield product_loader.load_item()
    '''
