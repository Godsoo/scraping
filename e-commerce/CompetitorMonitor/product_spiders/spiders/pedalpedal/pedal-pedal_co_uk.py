import re
import urllib

from decimal import Decimal
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

class PedalPedalCoUkSpider(BaseSpider):
    name = 'pedal-pedal.co.uk'
    allowed_domains = ['pedal-pedal.co.uk']
    start_urls = ('http://www.pedal-pedal.co.uk',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//a[@class="level-top"]'):
            href = url.select(u'./@href').extract()[0]
            if href in ('http://www.pedal-pedal.co.uk/shop-by-brand.html',):
                continue

            yield Request(href,
                    meta={'category': url.select(u'normalize-space(./span/text())').extract()[0]}
                    ,callback=self.parse_product_list)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//ul[@class="products"]/li/div/a/@href').extract():
            yield Request(url, meta=response.meta, callback=self.parse_product)

        next_page = hxs.select(u'//a[contains(@title,"Next")]/@href').extract()
        if next_page:
            yield Request(next_page[0], meta=response.meta, callback=self.parse_product_list)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1//text()')
        product_loader.add_xpath('price', u'//span[@class="price"]/text()')

        product_loader.add_xpath('identifier', u'//input[@name="product"]/@value');
        product_loader.add_xpath('sku', u'//input[@name="product"]/@value');
#        product_loader.add_xpath('category', u'//div[@class="breadcrumbs"]/ul/li[2]/a/text()')
        product_loader.add_value('category', response.meta.get('category'))

        product_loader.add_xpath('image_url', u'//div[contains(@class,"product-image-preview")]/img/@src')
        product_loader.add_xpath('brand', u'//td[@class="label" and contains(text(), "Manufacturer")]/../td[2]/text()')
#            product_loader.add_xpath('shipping_cost', '')
        product = product_loader.load_item()
        data_table = hxs.select(u'//div[@class="product-group"]//tbody/tr')
        if data_table:
            for row in data_table:
                prod = Product(product)
                prod['name'] = row.select(u'normalize-space(./td[1]/text())').extract()[0]
                prod['price'] = extract_price(row.select(u'.//span[@class="price"]/text()').extract()[0])
                prod['identifier'] = prod['identifier'] + row.select(u'substring(.//span[@class="price"]/@id,6)').extract()[0]
                yield prod
        else:
            yield product

