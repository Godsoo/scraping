# -*- coding: utf-8 -*-
import os
import csv
import paramiko
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import excel_to_csv
from urlparse import urljoin as urljoin_rfc
from product_spiders.utils import extract_price_eu as extract_price
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT
from scrapy.utils.url import add_or_replace_parameter

HERE = os.path.abspath(os.path.dirname(__file__))


class SubmarinoSpider(BaseSpider):
    name = u'bi_worldwide_br-submarino.com.br'
    allowed_domains = ['submarino.com.br']
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

        last, format_ = get_last_file('BI BRA File', files)

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

        url = 'http://busca.submarino.com.br/busca.php?results_per_page=90'
        for brand in self.brands:
            url = add_or_replace_parameter(url, 'q', brand)
            yield Request(url, callback=self.parse_products_list)

    def parse_products_list(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//*[@id="vitrine"]/article//a[@class="prodTitle"]/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        # pagination
        for url in hxs.select('//div[@class="result-pagination"]//li[@class="neemu-pagination-inner"]/a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_products_list)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        not_available = hxs.select('//div[@class="prod-unavailable"]')
        if not_available:
            return
        options = hxs.select('//form[@class="buy-form"]//select[@name="codItemFusion"]/option')
        if options:
            option_identifiers = options.select('./@value').extract()
            option_names = options.select('./text()').extract()
            options = dict(zip(option_identifiers, option_names))
            options = dict((k, v) for k, v in options.iteritems() if v)
        else:
            options = hxs.select('//form[@class="buy-form"]//input[@name="codItemFusion"]')
            if options:
                option_identifiers = options.select('./@value').extract()
                option_names = options.select('./@data-value-name').extract()
                options = dict(zip(option_identifiers, option_names))
                options = dict((k, v) for k, v in options.iteritems() if v)

        brand = hxs.select('//div[@class="area-tecnica"]//th[contains(text(),"Marca")]/../td/text()').extract()
        brand = brand[0].strip() if brand else ''
        name = hxs.select('//h1/span[@itemprop="name"]/text()').extract()[0].strip()
        identifier = hxs.select('//input[@name="codProdFusion"]/@value').extract()[0]
        price = hxs.select('//span[@itemprop="price"]/text()').extract()
        price = extract_price(price[0])
        category = hxs.select('//div[@class="breadcrumb"]//span[@itemprop="name"]/text()').extract()[:-1]
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        image_url = urljoin_rfc(base_url, image_url[0]) if image_url else ''

        if not options:
            if identifier in self.identifiers:
                return
            else:
                self.identifiers.append(identifier)
            loader = ProductLoader(item=Product(), selector=hxs)
            loader.add_value('brand', brand)
            loader.add_value('name', name)
            loader.add_value('price', price)
            loader.add_value('url', response.url)
            loader.add_value('identifier', identifier)
            loader.add_value('category', category)
            loader.add_value('image_url', image_url)
            yield loader.load_item()
        else:
            for option_identifier, option_name in options.iteritems():
                if option_identifier in self.identifiers:
                    continue
                else:
                    self.identifiers.append(option_identifier)
                loader = ProductLoader(item=Product(), selector=hxs)
                loader.add_value('brand', brand)
                loader.add_value('name', name + ' ' + option_name)
                loader.add_value('price', price)
                loader.add_value('url', response.url)
                loader.add_value('identifier', option_identifier)
                loader.add_value('category', category)
                loader.add_value('image_url', image_url)
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
