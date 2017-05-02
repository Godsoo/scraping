import csv
import os
import re
# from scrapy.spider import BaseSpider
from scrapy.contrib.spiders import SitemapSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.fuzzywuzzy import process
from product_spiders.fuzzywuzzy import fuzz

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class DigitalCameraWarehouseSpider(SitemapSpider):
    name = 'digitalcamerawarehouse.com.au'
    allowed_domains = ['digitalcamerawarehouse.com.au']
    # start_urls = ['http://www.digitalcamerawarehouse.com.au/']
    sitemap_urls = ['http://www.digitalcamerawarehouse.com.au/sitemap.xml', ]
    sitemap_rules = [
        ('/prod(\d)+\.htm', 'parse_product'),
    ]

    def start_urls(self):
        for request in list(super(DigitalCameraWarehouseSpider, self).start_urls()):
            yield request

        yield Request('http://www.digitalcamerawarehouse.com.au/')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        categories = hxs.select('//ul[@id="menu"]//a/@href').extract()
        for category in categories:
            url = urljoin_rfc(get_base_url(response), category)
            yield Request(url, self.parse_products)

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//div[@id="ProductDetails"]/div[@id="ProductDetails"]')
        if products:
            for product in products:
                url = product.select('div/div[@id="ProductName"]/h2/a/@href').extract()
                if url:
                    url = urljoin_rfc(get_base_url(response), url[0])
                else:
                    url = product.select('tr/td/div/strong/a/@href').extract()
                    if url:
                        url = urljoin_rfc(get_base_url(response), url[0])
                yield Request(url, callback=self.parse_product)
                """
                try:
                    identifier = re.search(r'/prod(\d+)', url).groups()[0]
                except:
                    # Options
                    yield Request(url, callback=self.parse_products)
                    continue

                loader = ProductLoader(item=Product(), selector=product)
                loader.add_xpath('name', 'div/div[@id="ProductName"]/h2/a/text()')
                loader.add_value('url', url)
                price = product.select('div/div/div[@class="Cart-ProductCost"]/text()').extract()
                if price:
                    price = price[0]
                else:
                    price = '0.0'
                loader.add_value('price', price)
                category = hxs.select('//div[@class="SiteMap"]/a/text()').extract()
                category = category[-2] if category else ''
                loader.add_value('category', category)
                loader.add_value('identifier', identifier)

                try:
                    loader.add_value('image_url',
                                     urljoin_rfc(get_base_url(response),
                                                 product.select('.//a/img/@src')
                                                 .extract()[0]))
                except:
                    pass

                out_stock = product.select('.//div[@class="Cart-Special-Note" and contains(text(), "This product is coming soon")]/text()').extract()
                if out_stock:
                    loader.add_value('stock', 0)

                yield loader.load_item()
                """
        else:
           try:
               categories = hxs.select('//td[@class="td"]/div[@style="width:750px;'
                                       ' padding: 10px 0px 10px 20px; "]/'
                                       'table[@cellpadding="5"]')
               if categories:
                   for category in categories:
                       url = urljoin_rfc(get_base_url(response),
                                         category.select('tr/td/a[@class="HeadingText"]/@href').extract()[0])
                       yield Request(url, dont_filter=True, callback=self.parse_products)
           except IndexError:
               pass


        sub_categories = hxs.select('//div[@class="CategoryContainer"]//tr/td/font/a/@href').extract()
        sub_categories = hxs.select('//div[@id="ProductDetails"]/a/@href').extract()
        for sub_category in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_category)
            yield Request(url, callback=self.parse_products)

        html = hxs.extract().replace('Sub Categories', '<div id="sub_categories">').replace('<p> </p>', '</div>')
        new_hxs = HtmlXPathSelector(text=html)
        sub_categories = new_hxs.select('//*[@id="sub_categories"]/a/@href').extract()
        for sub_category in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_category)
            yield Request(url, dont_filter=True, callback=self.parse_products)

        sub_categories = hxs.select('//div[@id="ProductDetails"]/a/@href').extract()
        for sub_category in sub_categories:
            url = urljoin_rfc(get_base_url(response), sub_category)
            yield Request(url, callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        identifier = re.search(r'/prod(\d+)', response.url).groups()[0]

        loader = ProductLoader(item=Product(), selector=hxs)

        try:
            category = hxs.select('//div[@class="SiteMap"]/a/text()').extract()[-1]
            loader.add_value('category', category)
        except:
            pass

        try:
            image_url = hxs.select('//div[@class="html5gallery"]//img[contains(@src, "productimage_")]/@src').extract()[0].split('?')[0]
            image_url = urljoin_rfc(get_base_url(response), image_url)
                
            loader.add_value('image_url', image_url)
        except:
            try:
                image_url = hxs.select('//div[@id="Product-Left-TopOld"]/img/@src').extract()[0].split('?')[0]
                image_url = urljoin_rfc(get_base_url(response), image_url)
                loader.add_value('image_url', image_url)
            except:
                pass

        loader.add_xpath('name', '//div[contains(@id, "ProductName")]/h1/text()')
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('price', '//div[@class="Cart-ProductCost"]/text()')
        sku = hxs.select('//p[b[contains(text(), "Product Code")]]/text()').extract()
        sku = sku[0].strip() if sku else ''
        loader.add_value('sku', sku)

        out_stock = hxs.select('.//div[@class="Cart-Container"]/div[@class="Cart-Special-Note" and contains(text(), "This product is coming soon")]/text()').extract()
        if out_stock:
            loader.add_value('stock', 0)

        not_available = hxs.select('//div[@id="Product-NotAvailable"]')
        if not not_available:
            yield loader.load_item()
