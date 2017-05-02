import re
import os
import hashlib
import csv
import copy
import json
import itertools
from urllib import urlencode
from urlparse import urljoin

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from scrapy.shell import inspect_response

HERE = os.path.abspath(os.path.dirname(__file__))

class PoshRoshSpider(BaseSpider):
    name = 'lecreuset-poshrosh.co.uk'
    #download_delay = 3
    allowed_domains = ['poshrosh.co.uk']
    start_urls = ['http://www.poshrosh.co.uk/categorydetails.aspx?bId=277']

    def start_requests(self):
        yield Request('http://www.poshrosh.co.uk/categorydetails.aspx?bId=277', callback=self.parse_pagination)

    def parse_pagination(self, response):
        hxs = HtmlXPathSelector(response)
        formdata = {}
        formdata['__EVENTVALIDATION'] = hxs.select('//input[@name="__EVENTVALIDATION"]/@value').extract()[0]
        formdata['__VIEWSTATE'] = hxs.select('//input[@name="__VIEWSTATE"]/@value').extract()[0]
        formdata['__EVENTTARGET'] = 'ctl00$ContentPlaceHolder1$ViewAllId'
        formdata['__EVENTARGUMENT'] = ''
        yield FormRequest(response.url, formdata=formdata)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//div[@class="additem"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        identifier = re.search('pId=(.*)&', response.url)
        if identifier:
            loader.add_value('identifier', identifier.group(1))
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        sku = hxs.select('//div[@class="CatNo"]/span/following-sibling::text()')[0].re('(\d+)')
        if len(sku) > 1:
            sku = ' '.join(sku)
        loader.add_value('sku', sku)
        name = hxs.select('//div[@class="HeaderProductName"]/text()').extract()
        loader.add_value('name', name)
        #price
        price = hxs.select('//label[@class="TotalSalesPrice"]/text()')[0].extract().strip()
        loader.add_value('price', price)
        #image_url
        image_url = hxs.select('//img[@id="imgMain"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        #brand
        loader.add_value('brand', 'Le Creuset')
        #category
        loader.add_value('category', 'Le Creuset')
        #shipping_cost
        loader.add_value('shipping_cost', '4.99')


        yield loader.load_item()