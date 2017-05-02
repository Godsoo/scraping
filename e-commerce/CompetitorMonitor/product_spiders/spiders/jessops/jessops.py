import re
import json
import os
import csv
import paramiko

import urllib

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.item import Item, Field

from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class JessopsMeta(Item):
    promotion = Field()


class JessopsSpider(BaseSpider):
    name = 'jessops-jessops.com'
    allowed_domains = ['jessops.com']

    start_urls = ['http://www.jessops.com/']

    def parse(self, response):
        base_url = get_base_url(response)

        file_path = HERE + '/jessops_sku.csv'

        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row['sku'].strip()
                search_url = "http://www.jessops.com/search?q=" + sku
                yield Request(search_url, callback=self.parse_search)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        results = hxs.select('//a[@class="productDataUrl"]/@href').extract()
        yield Request(results[0], callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
 
        loader = ProductLoader(response=response, item=Product())
        loader.add_xpath('identifier', '//input[@name="skuOfferingId1"]/@value')
        sku = hxs.select('//span[@id="mainprodsku"]/text()').re('Product code: (.*)')
        loader.add_value('sku', sku)
        categories = hxs.select('//div[@id="breadcrumbtrail"]/a/text()').extract()[1:]
        brand = re.findall("manufacturerName: '(.*)'", response.body)
        brand = brand[0] if brand else ''
        loader.add_value('brand', brand)
        loader.add_value('category', categories)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        price = hxs.select('//span[@itemprop="price"]/text()').extract()[0]
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        image_url = hxs.select('//img[@id="imgRegular"]/@src').extract()
        image_url = urljoin_rfc(get_base_url(response), image_url[0].strip()) if image_url else ''
        loader.add_value('image_url', image_url)

        promotion = ' '.join(''.join(hxs.select('//div[@id="promomessage"]//text()').extract()).split())
        metadata = JessopsMeta()
        metadata['promotion'] = promotion

        product = loader.load_item()
        product['metadata'] = metadata
        yield product
