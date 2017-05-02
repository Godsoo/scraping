import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from scrapy import log
from scrapy.shell import inspect_response

from urlparse import urljoin

import itertools
import json
import copy
import lxml

HERE = os.path.abspath(os.path.dirname(__file__))

class EcookshopSpider(BaseSpider):
    name = 'ecookshop'
    #download_delay = 3
    allowed_domains = ['ecookshop.co.uk']
    start_urls = ['http://www.ecookshop.co.uk/ecookshop/le-creuset.asp']
    #cookie_num = 0
    #brands = []
    id_seen = []

    def parse(self, response):
        #inspect_response(response, self)
        #yield Request('http://www.ecookshop.co.uk/ecookshop/product.asp?pid=962009161', callback=self.parse_product)
        #return
        hxs = HtmlXPathSelector(response)
        for link in hxs.select('//a[@class="ecookshopsidemenu"]/@href').extract()[1:]: ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

        return ###
        for link in hxs.select('//a[@class="ecstdlink" and img]/@href').extract(): ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)
        #links = hxs.select('//tr[td/@class="ecookshopproducthead"]/following-sibling::tr/td/a[1]/@href').extract()
        #if not links:
        #    links = hxs.select('//table[@class="hoverTable"]//a[1]/@href').extract()
        #if not links:
        #    links = hxs.select('//td/a[@class="ecstdlink"][1]/@href').extract()
        #if not links:
        links = hxs.select('//a[contains(@href,"/ecookshop/product.asp?pid")]/@href').extract()
        for link in links: ###
            url = urljoin(response.url, link)
            yield Request(url, callback=self.parse_product)

        #To crawl next page.
        return ###
        tmp = None
        if tmp:
            #url = urljoin(response.url, tmp[0])
            yield Request(tmp[0], callback=self.parse_products_list)

    def parse_product(self, response):
        #inspect_response(response, self)
        #return
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('url', response.url)
        tmp = hxs.select('//span[@itemprop="identifier"]/text()').extract()
        if tmp:
            loader.add_value('identifier', tmp[0].strip())
            loader.add_value('sku', tmp[0])
        else:
            log.msg('### No product ID at '+response.url, level=log.INFO)
            return
        #tmp = hxs.select('//input[@name="productId"]/@value').extract()
        #if tmp:
        #    loader.add_value('sku', tmp[0])
        name = ''
        tmp = hxs.select('//span[@itemprop="name"]/h1/text()').extract()
        if tmp:
            name = tmp[0].strip()
            loader.add_value('name', name)
        else:
            log.msg('### No name at '+response.url, level=log.INFO)
        #price
        price = 0
        tmp = hxs.select('//span[@itemprop="price"]/text()').extract()
        if tmp:
            price = extract_price(tmp[0].strip().replace(',',''))
            loader.add_value('price', price)
        #stock
        stock = 0
        tmp = hxs.select('//td[strong="In Stock: "]/text()').extract()
        if tmp and 'yes' in ''.join(tmp).lower():
            stock = 1
        tmp = hxs.select('//td[span/@itemprop="identifier"]/preceding-sibling::td/text()').extract()
        if tmp and 'availability' in ''.join(tmp).lower():
            stock = 1
        loader.add_value('stock', stock)
        #image_url
        tmp = hxs.select('//img[@itemprop="image"]/@src').extract()
        if not tmp:
            tmp = hxs.select('//td[@width="350"]/img/@src').extract()
        if tmp:
            url = urljoin(response.url, tmp[0])
            loader.add_value('image_url', url)
        #brand
        tmp = hxs.select('//span[@itemprop="brand"]/text()').extract()
        if not tmp or tmp[0].lower()!='Le Creuset'.lower():
            log.msg('### It is not brand Le Creuset at '+response.url, level=log.INFO)
            return
        loader.add_value('brand', 'Le Creuset')
        #category
        loader.add_value('category', 'Le Creuset')
        #shipping_cost
        if price<20:
            loader.add_value('shipping_cost', 2.49)
        elif price<50:
            loader.add_value('shipping_cost', 5.95)
        #promotional
        promotional = []
        tmp = hxs.select('//td[strong/font//span/@itemprop="price"]/text()').extract()
        if tmp:
            txt = ''.join(tmp)
            r = re.findall(r'\(Save - \d+%\)', txt)
            if r:
                promotional.append(r[0])
        tmp = hxs.select('//td[@bgcolor="#C00000"]').extract()
        if tmp:
            txt = '\n'.join([lxml.html.fromstring(s.replace('<br>', '\n').strip()).text_content() for s in tmp if len(s.strip())>0])
            promotional.append(txt.strip())
        features = ''
        tmp = hxs.select('//td[strong="Features:"]/span[@itemprop="description"]').extract()
        if tmp:
            features = '\n'.join([lxml.html.fromstring(s.replace('<br>', '\n').strip()).text_content() for s in tmp if len(s.strip())>0])
        loader.add_value('metadata', {'promotional':promotional, 'features':features})

        product = loader.load_item()

        options = None
        #No options currently.
        if not options:
            if not product.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not product['identifier'] in self.id_seen:
                    self.id_seen.append(product['identifier'])
                    yield product
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)
            return
        #process options
        #No options currently.
        for sel in options[0:1]: ###
            item = copy.deepcopy(product)
            tmp = sel.select('.//label/input/@value').extract()
            if tmp:
                item['identifier'] += '-' + tmp[0]
                item['name'] = name + ' - ' + tmp[0]

            if not item.get('identifier', None):
                log.msg('### No product ID at '+response.url, level=log.INFO)
            else:
                if not item['identifier'] in self.id_seen:
                    self.id_seen.append(item['identifier'])
                    yield item
                else:
                    log.msg('### Duplicate product ID at '+response.url, level=log.INFO)

