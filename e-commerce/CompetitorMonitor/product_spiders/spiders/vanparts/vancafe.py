import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

import csv

from product_spiders.items import Product, ProductLoader


class VanCafeSpider(BaseSpider):
    name = 'van-cafe.com'
    allowed_domains = ['www.van-cafe.com']
    start_urls = ('http://www.van-cafe.com/',)

    def __init__(self, *args, **kwargs):
        super(VanCafeSpider, self).__init__(*args, **kwargs)

        self.identifiers = []

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select('//div[@id="midnav"]/div[@class="midnavlinks"]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        # subcategories
        subcategories = hxs.select('//td[not(child::a[not(child::img)])]/span[@class="cellheader"]//a/@href').extract()
        for url in subcategories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        # pages
        next_page = hxs.select('//span[@class="nextprev"]/a[contains(text(),"Next")]/@href').extract()
        if next_page:
            url = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(url)

        # products
        for product in self.parse_products(response):
            yield product


    def parse_products(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)

        # products
        products = hxs.select('//div[@id="mtbody"]//table//table//a/img/../..')

        for product in products:
            product_loader = ProductLoader(item=Product(), selector=product)
            # product_loader.add_xpath('name', './/span[@class="cellheader"]/a/text()')
            product_loader.add_xpath('price', './/span[@class="pricetext"]/text()',
                                     re='.*\$(.*[0-9])')
            sku = product.select('.//span[@class="sku"]/text()').extract()
            if not sku:
                continue
            identifier = sku[0].strip()
            if identifier in self.identifiers:
                continue
            else:
                self.identifiers.append(identifier)
            product_loader.add_value('identifier', identifier)
            sku = re.sub('[.\- ]', '', sku[0])
            product_loader.add_value('sku', sku)
            product_loader.add_xpath('name', './/span[@class="cellheader"]/a/text()')

            url = product.select('.//span[@class="cellheader"]/a/@href').extract()
            if not url:
                continue
            url = urljoin_rfc(get_base_url(response), url[0])
            product_loader.add_value('url', url)
            yield Request(url, callback=self.parse_product, meta={'loader': product_loader})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        product_loader = response.meta['loader']

        name = product_loader.get_output_value('name')
        image = hxs.select('//img[contains(@src, "shop/images/")]/@src').extract()
        if image:
            product_loader.add_value('image_url', image)
        outstock = hxs.select('//span[contains(text(), "Sorry, this item is out of stock.")]')
        if outstock:
            product_loader.add_value('stock', 0)
        category = hxs.select('//span[@class="insertlist1"]/a/text()').extract()
        if category:
            product_loader.add_value('category', category[-1].strip())
        yield product_loader.load_item()
