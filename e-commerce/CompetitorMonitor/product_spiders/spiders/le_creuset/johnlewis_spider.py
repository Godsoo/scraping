import re
import os
import csv
import shutil

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from scrapy.http import Request, HtmlResponse

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

HERE = os.path.abspath(os.path.dirname(__file__))


class JohnLewisSpider(BaseSpider):
    name = 'lecreuset-johnlewis.com'
    allowed_domains = ['johnlewis.com']
    start_urls = ['http://www.johnlewis.com/home-garden/home-brands/le-creuset/c600001725']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        for cat in hxs.select('//section[contains(@class, "lt-nav-container-links")]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), cat))

        products = hxs.select("//div[@class='products']/div/article//a[@class='product-link'][1]/@href").extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), self.parse_product)

        next_page = filter(lambda link: link != '#', hxs.select('//li[@class="next"]//a[@rel="next"]/@href').extract())

        if next_page:
            yield Request(url=urljoin_rfc(base_url, next_page[0]))


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        colour_options = hxs.select('//ul[@class="selection-grid"]/li/a/@href').extract()
        for colour_option in colour_options:
            yield Request(urljoin_rfc(base_url, colour_option), callback=self.parse_product)


        name = hxs.select('normalize-space(//*[@itemprop="name"]/text())').extract()[0]
        ext_name = ''.join(hxs.select('//h1[@id="prod-title"]/text()').extract()).strip().replace(u'\xa0', ' ')

        name = name + ' ' + ext_name if ext_name else name

        brand = hxs.select('normalize-space(//*[@itemprop="brand"]/span/text())').extract()

        try:
            image_url = urljoin_rfc(base_url,
                                    hxs.select('//div[@id="prod-media-player"]'
                                               '//img/@src').extract()[0].strip())
        except IndexError:
            image_url = ''


        set_items = hxs.select('//div[@class="item-details"]/a/@href').extract()
        if set_items:
            for item in set_items:
                yield Request(urljoin_rfc(base_url, item), self.parse_product)
            return


        options = hxs.select('//div[@id="prod-multi-product-types"]')

        if options:
            products = options.select('.//div[@class="product-type"]')
            for product in products:
                opt_name = product.select('.//h3/text()').extract()[0].strip()
                try:
                    stock = product.select('//div[contains(@class, "mod-stock-availability")]'
                                           '//p/strong/text()').re(r'\d+')[0]
                except IndexError:
                    stock = 0

                loader = ProductLoader(item=Product(), selector=product)
                sku = product.select('.//div[contains(@class, "mod-product-code")]/p/text()').extract()
                if sku:
                    loader.add_value('sku', sku[0].strip())
                loader.add_xpath('identifier', './/div[contains(@class, "mod-product-code")]/p/text()')
                loader.add_value('name', '%s %s' % (name, opt_name))
                loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[@class="last"]/a/text()')
                loader.add_value('image_url', image_url)
                loader.add_value('brand', brand)
                loader.add_value('url', response.url)
                loader.add_xpath('price', './/p[@class="price"]/strong/text()')
                loader.add_value('stock', stock)
                yield loader.load_item()
        else:
            price = ''.join(hxs.select('//ul/li/strong[@class="price"]/text()').extract()).strip()
            if not price:
                price = ''.join(hxs.select('//div[@id="prod-price"]//strong/text()').extract()).split()
                if not price:
                    price = ''.join(hxs.select('//span[@class="now-price"]/text()').extract()).split()

            stock = hxs.select('//div[contains(@class, "mod-stock-availability")]/p[not(contains(@class, "hidden"))]//strong/text()').extract()
            stock = stock[0].strip() if stock else ''

            loader = ProductLoader(item=Product(), response=response)
            sku = hxs.select('//div[@id="prod-product-code"]/p/text()').extract()
            if not sku:
                sku = ''
            loader.add_xpath('identifier', '//div[@id="prod-product-code"]/p/text()')
            loader.add_value('name', name)
            loader.add_xpath('category', '//div[@id="breadcrumbs"]//li[@class="last"]/a/text()')
            loader.add_value('image_url', image_url)
            loader.add_value('brand', brand)
            loader.add_value('url', response.url)
            loader.add_value('price', price)
            loader.add_value('sku', sku)
            if 'OUT OF STOCK' in stock.upper():
                loader.add_value('stock', 0)
            else:
                stock_value = extract_price(stock)
                if stock_value>0 and 'IN STOCK' not in stock:
                    loader.add_value('stock', stock_value)

            if loader.get_output_value('price')<50:
                loader.add_value('shipping_cost', 3)
            yield loader.load_item()
