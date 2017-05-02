import csv
import os
import xlrd
import json
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request

from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoader
from urlparse import urljoin

HERE = os.path.abspath(os.path.dirname(__file__))


class RakutenCoUk(BaseSpider):
    name = 'thebookpeople-rakuten.co.uk'
    allowed_domains = ['www.rakuten.co.uk']
    start_urls = []
    base_url = 'http://www.rakuten.co.uk/search/{isbn}/?l-id=search_regular'

    def start_requests(self):
        """Set up the search urls"""
        with open(os.path.join(HERE, 'thebookpeople.co.uk_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                yield Request(
                    # self.base_url.format(isbn=row['ISBN'])
                    self.base_url.format(isbn=row['sku'])
                )

    def parse(self, response):
        """Extract the results of the search"""
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        product_xpath = "//div[contains(concat('',@class,''), 'b-item-list-box-container')]//li[@class='b-item']//a[img]/@href"

        for href in hxs.select(product_xpath).extract():
            yield Request(
                urljoin(base_url, href),
                callback=self.parse_product
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sku = hxs.select('//input[@name="sku"]/@value').extract()
        name = hxs.select('//h1[@class="b-ttl-main"]/text()').extract()[0]
        brand = hxs.select('.//span[@itemprop="brand"]/text()').extract()
        if brand:
            brand = brand[0].strip()
        else:
            brand = response.meta.get('brand')

        categories = hxs.select('//ul[@class="b-breadcrumb"]/li/a/text()').extract()
        #image_url = hxs.select('//div[contains(@class, "b-main-image")]/a/img/@data-frz-src').extract()
        image_url = hxs.select('//img[@itemprop="image"]/@data-frz-src').extract()

        options = hxs.select('//script[contains(text(), "var variant_details")]/text()').extract()
        if options:
            options = options[0].replace('&quot;', "'")
            options = re.findall('var variant_details = (.*);\n', options)
            variants = json.loads(options[0])
        else:
            identifier = hxs.select('//input[@name="item_id"]/@value').extract()[0]
            price = hxs.select('//div[@class="b-product-main"]//meta[@itemprop="price"]/@content').extract()[0]
            variants = [{'itemVariantId': identifier, 'variantValues': [], 'defaultPricing': {'price': price}}]

        for variant in variants:
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('identifier', variant['itemVariantId'])
            loader.add_value('name', " ".join([name] + variant.get('variantValues', [])))
            loader.add_value('url', response.url)
            loader.add_value('price', variant['defaultPricing']['price'])
            loader.add_value('category', categories)
            if sku:
                loader.add_value('sku', sku[0])
            if brand:
                loader.add_value('brand', brand)
            if image_url:
                loader.add_value('image_url', image_url[0])
            product = loader.load_item()

            yield product
