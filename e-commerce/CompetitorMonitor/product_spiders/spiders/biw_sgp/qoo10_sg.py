# -*- coding: utf-8 -*-
import os
import re
import csv
import paramiko
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import excel_to_csv
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from scrapy.utils.url import add_or_replace_parameter

HERE = os.path.abspath(os.path.dirname(__file__))


class Qoo10SgSpider(BaseSpider):
    name = u'bi_worldwide_sg-www.qoo10.sg'
    allowed_domains = ['qoo10.sg']
    start_urls = ('http://www.biworldwide.com', )
    brands = []
    identifiers = []

    def parse(self, response):

        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "p02SgdLU"
        username = "biw"
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last, format_ = get_last_file('BI SGP File', files)

        file_path = os.path.join(HERE, 'biw_products.csv')
        if format_ == 'csv':
            sftp.get(last.filename, file_path)
        else:
            file_path_excel = os.path.join(HERE, 'biw_products.xlsx')
            sftp.get(last.filename, file_path_excel)
            excel_to_csv(file_path_excel, file_path)

        with open(file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                try:
                    brand = unicode(row['BI Brand'], errors='ignore').strip()
                    if brand not in self.brands:
                        self.brands.append(brand)
                except:
                    pass

        url = 'http://list.qoo10.sg/s/?keyword=ff'
        for brand in self.brands:
            # remove articles from brand and small words
            brand = re.sub(r'\W*\b\w{1,2}\b','', brand.lower())
            brand = re.sub('(\s+)(and|the)(\s+)', ' ', brand)
            url = add_or_replace_parameter(url, 'keyword', brand)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//*[@id="search_result_item_list"]/dd//p[@class="subject"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        # pagination
        for url in hxs.select('//*[@id="pageing_list"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//h2[@class="name"]/text()').extract()[0]
        dealer = hxs.select('//div[@class="mshop_bar"]//div[@class="name"]/a/text()').extract()
        dealer = dealer[0].strip() if dealer else ''

        identifier = response.url.split('/')[-1]

        if identifier in self.identifiers:
            return
        else:
            self.identifiers.append(identifier)

        price = hxs.select('//strong[@data-price]/@data-price').extract()
        if price:
            price = extract_price(price[0])
        else:
            price = 0
        category = hxs.select('//dl[@class="category"]/dd/a/span/text()').extract()[0:3]
        image_url = hxs.select('//*[@id="GoodsImage"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('url', response.url)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('category', category)
        loader.add_value('image_url', image_url)
        loader.add_value('dealer', dealer)
        yield loader.load_item()


def get_last_file(start_with, files):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    format_ = 'csv'
    for f in files:
        if ((last is None and start_with in f.filename and
             f.filename.endswith('.csv')) or
            (start_with in f.filename and f.filename.endswith('.csv') and
             f.st_mtime > last.st_mtime)):
            last = f
    if not last:
        format_ = 'xlsx'
        for f in files:
            if ((last is None and start_with in f.filename and
                 f.filename.endswith('.xlsx')) or
                (start_with in f.filename and f.filename.endswith('.xlsx') and
                 f.st_mtime > last.st_mtime)):
                last = f
    return last, format_
