import re
import json

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class ExportPriveSpider(BaseSpider):
    name = 'exportprive.fr'
    allowed_domains = ['exportprive.fr']
    start_urls = ('http://www.exportprive.fr/fr/',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = (hxs.select('//ul[@id="menu"]/li//table[@class="columnWrapTable"]//ul/li/a/@href').extract() + 
                     hxs.select('//ul[@id="menu"]/li//table[@class="columnWrapTable"]/tr/td/div/div[not(ul)]/h5/a/@href').extract())
        for category_url in categories:
            yield Request(urljoin_rfc(base_url, category_url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        category_name = hxs.select('//div[@class="breadcrumb"]/text()').extract()[-1]
        products = hxs.select('//ul[@id="product_list"]/li/div/div/h4/a/@href').extract()
        for prod_url in products:
            yield Request(prod_url, callback=self.parse_product, meta={'category':category_name})

        next = hxs.select('//li[@class="pagination_next"]/a/@href').extract()
        if next:
            yield Request(next[-1], callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        identifier = hxs.select('//input[@id="product_page_product_id"]/@value').extract()
        identifier = identifier[0] if identifier else response.url.split('/')[-1].split('-')[0]

        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_xpath('name', '//div[@id="product_title"]/h1/text()')
        l.add_value('category', response.meta['category'])
        l.add_xpath('brand', '//a[@class="brand_image"]/@title')
        l.add_xpath('sku', '//h2[@id="product_reference"]/span/text()')
        l.add_value('url', response.url)
        price = hxs.select('//span[@id="our_price_display"]/text()').extract()
        if price:
            price = ''.join(price[0].replace(',', '.').split())
        else:
            price = 0
        #price = ''.join(price[0].strip().split()).replace(',','.') if price else 0
        l.add_value('price', price)
        l.add_xpath('image_url', '//div[@id="image-block"]/img/@src')
        yield l.load_item() 
