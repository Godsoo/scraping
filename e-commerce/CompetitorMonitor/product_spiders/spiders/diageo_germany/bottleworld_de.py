import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price_eu
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


class BottleWorldSpider(BaseSpider):
    name = 'bottleworld.de'
    allowed_domains = ['bottleworld.de']
    start_urls = ('http://bottleworld.de',)

    def _start_requests(self):
        yield Request('http://www.bottleworld.de/bier/augustiner/augustiner-dunkel.html', callback=self.parse_product, meta={'product': Product()})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for cat in hxs.select('//ul[@id="nav"]//a[@class="level-top"]'):
            yield Request(urljoin_rfc(get_base_url(response), cat.select('./@href').extract()[0]),
                    callback=self.parse_cat,
                    meta={'category': cat.select('./span/text()').extract()[0]})

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for productxs in hxs.select('//li[@class="item last span3"]') + hxs.select('//li[@class="item first span3"]'):
            product = Product()
            price = extract_price_eu(''.join(productxs.select('.//span[starts-with(@id,"product-price-")]//text()').extract()))
            if productxs.select('.//span[contains(@class,"delivery_status_red")]') or productxs.select('.//span[contains(text(),"noch nicht lieferbar")]'):
                product['stock'] = '0'
            else:
                product['stock'] = '1'

            meta = response.meta.copy()
            meta['product'] = product
            meta['price'] = price

            yield Request(urljoin_rfc(get_base_url(response), productxs.select('.//h2/a/@href').extract()[0]),
                          callback=self.parse_product, meta=meta)

        for page in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), page), callback=self.parse_cat, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=response.meta['product'], selector=hxs)

        category = hxs.select('//li[starts-with(@class,"category")]/a/text()').extract()
        price = hxs.select('//div[@class="product-view"]//span[@class="price"]/text()').extract()
        if category:
            loader.add_value('category', category[0])
        else:
            loader.add_value('category', response.meta.get('category'))
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//*[@itemprop="name"]//text()')
        loader.add_xpath('sku', '//input[@name="product"]/@value')
        if price:
            loader.add_value('price', extract_price_eu(price.pop()))
        else:
            loader.add_value('price', response.meta['price'])

        img = hxs.select('//img[@itemprop="image"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))

        for brand in hxs.select('//ul[@id="nav"]//a[not(@class="level-top")]'):
            url = brand.select('./@href').extract()[0]
            if response.url.startswith(url + '/'):
                loader.add_value('brand', ''.join(brand.select('./span/text()').extract()))
        yield self.add_shipping_cost(loader.load_item())

    def add_shipping_cost(self, item):
        if item.get('price', 0) < 130:
            item['shipping_cost'] = 5.99
        else:
            item['shipping_cost'] = 0
        return item
