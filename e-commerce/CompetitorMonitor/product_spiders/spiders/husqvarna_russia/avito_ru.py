# -*- coding: utf-8 -*-
import os
import xlrd
import paramiko

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from urlparse import urljoin as urljoin_rfc

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class BestSadRuSpider(BaseSpider):
    name = u'husqvarna-russia-avito.ru'
    allowed_domains = ['avito.ru']
    start_urls = ['https://www.avito.ru']

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "g45dR5dz"
        username = "husqvarna"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        #last = get_last_file("husqvarna_russia", files)
        file_path = HERE+'/husqvarna.xlsx'

        wb = xlrd.open_workbook(file_path)
        sh = wb.sheet_by_name('Products')

        search_url = "https://www.avito.ru/moskva?q="
        for rownum in xrange(sh.nrows):
            if rownum < 2:
                continue

            row = sh.row_values(rownum)
            yield Request(search_url+row[1], meta={'brand': row[1]})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="context-flyer__title fader"]/a/@href').extract()
        products += hxs.select('//div[@class="description"]/h3/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product, meta=response.meta)

        next = hxs.select(u'//div[@class="pagination__nav clearfix"]/a[contains(text(), "\u2192")]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        image_url = hxs.select('//div[contains(@class, "picture-wrapper")]/div/img/@src').extract()
        product_identifier = hxs.select('//span[@id="item_id"]/text()').extract()
        if not product_identifier: 
            log.msg('PRODUCT WITHOUT IDENTIFIER: ' + response.url)
            return
        product_identifier = product_identifier[0].strip()
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('identifier', product_identifier)
        loader.add_value('name', product_name)
        loader.add_value('sku', product_identifier)
        if image_url:
            loader.add_value('image_url', 'https://' + image_url[0])
        price = ''.join(''.join(hxs.select('//span[@itemprop="price"]/text()').extract()).split())
        if price:
            loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta['brand'].title())
        categories = hxs.select('//div[@class="b-catalog-breadcrumbs"]/a/text()').extract()[-3:]
        for category in categories:
            loader.add_value('category', category)
        dealer = hxs.select('//div[@id="seller"]/strong/text()').extract()
        dealer = dealer[0].strip() if dealer else ''
        loader.add_value('dealer', dealer)
        product = loader.load_item()
        yield product
