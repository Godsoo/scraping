import re
import urllib
from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import unicodedata


class TropicanafitnessComSpider(BaseSpider):
    name = 'tropicanafitness.com'
    allowed_domains = ['tropicanafitness.com']
    start_urls = ['http://www.tropicanafitness.com/category/search?layout=grid&sort=rating&searchterm=&page=1']

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)

        yield Request('http://www.tropicanafitness.com/category',
                      callback=self.parse_categories)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//div[@class="pagination"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, meta=response.meta)

        for url in hxs.select(u'//li[@class="prod"]//h5/a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product, meta=response.meta)

    def get_options(self, hxs):
        ids = hxs.select(u'//div[@class="product-options"]//option[@value!=""]/@value').extract()
        names = hxs.select(u'//div[@class="product-options"]//option[@value!=""]/text()').extract()
        return zip(ids, names)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//div[@id="product-details-main"]//h1/text()')
        product_loader.add_xpath('category', u'//div[@class="crumbs"]/a[2]/text()')
        product_loader.add_xpath('price', u'//span[@class="blu-price"]/span/text()')

        product_loader.add_xpath('sku', '//meta[@name="bc:sku"]/@content')

        img = hxs.select(u'//img[@id="product-image-main"]/@src').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        brands = hxs.select(u'//ul[@id="nav-top-list"]/li[contains(@class,"brands")]//a/text()').extract()
        name = product_loader.get_output_value('name').split()[0].lower()
        for brand in brands:
            if brand.split()[0].lower() == name:
                product_loader.add_value('brand', brand)

        product = product_loader.load_item()

        for variant in hxs.select('//div[@class="variant"]'):
            var_name = product['name'] + ' ' + variant.select('.//h4/text()').extract()[0].strip()
            price = variant.select('.//p[contains(@class, "price")]/span/text()').extract()[-1]
            for opt in variant.select('.//table/tr'):
                opt_name = var_name + ' ' + opt.select('td[1]/text()').extract()[0].strip()
                stock = opt.select('td[2]/text()').extract()[0].strip().lower()
                identifier = self.normalizename(opt_name).replace(' ', '')\
                    .replace('/', '').replace('-', '').replace('+', '').lower().replace('on sale', '').strip()
                opt_product = Product(product)
                opt_product['price'] = extract_price(price)
                opt_product['name'] = opt_name
                opt_product['identifier'] = identifier
                if 'out of stock' in stock:
                    opt_product['stock'] = 0
                yield opt_product

    def parse_categories(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for url in hxs.select('//div[@id="section-items-content"]/ul/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url))

    def normalizename(self, name):
        return unicodedata.normalize('NFKD', name)\
            .encode('ascii', 'ignore').replace(' ', '').lower()\
            .replace('/', '').replace('-', '').replace('+', '').replace('100%', '')\
            .replace('on sale', '').replace('!', '').replace('&', '').strip()

