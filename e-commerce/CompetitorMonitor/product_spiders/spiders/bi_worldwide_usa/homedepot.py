# -*- coding: utf-8 -*-
"""
Customer: BIW USA
Website: http://www.homedepot.com
Crawling process: search by brand using the client file from the SFTP and extract all results
Options: extract all options
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4023

IMPORTANT! the BREADCRUMB_JSON part isn't a valid JSON syntax, demjson is used to parse it.

IMPORTANT! the site redirects some pages adding a port number, like this: http://www.homedepot.com:8123
the spider checks the error status and reload the page without the port number

IMPORTANT! the retry method makes a request to the self.parse method because self.parse
checks both product list pages and product pages

"""

import os
import re
import csv
import xlrd
import demjson
import paramiko

import pandas as pd

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request

from scrapy import log

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.config import DATA_DIR
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))

class HomedepotSpider(BaseSpider):
    name = 'biwusa-homedepot.com'
    allowed_domains = ['homedepot.com', 'origin.api.homedepot.com']
    start_urls = ('http://www.homedepot.com',)
    errors = []

    handle_httpstatus_list = [404, 500, 504]

    brands = []

    file_start_with = 'BI USA File'

    xls_file_path = HERE + '/biw_products.xlsx'
    csv_file_path = HERE + '/biw_products.csv'

    options_identifiers = []


    def __init__(self, *args, **kwargs):
        super(HomedepotSpider, self).__init__(*args, **kwargs)

        dispatcher.connect(self.spider_idle, signals.spider_idle)

        self.new_ids = []

        self.try_deletions = True

    def _get_prev_crawl_filename(self):
        filename = None
        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
        return filename

    def spider_idle(self, spider):
        if self.try_deletions:
            self.try_deletions = False

            filename = self._get_prev_crawl_filename()
            if filename and os.path.exists(filename):
                old_products = pd.read_csv(filename, dtype=pd.np.str)
                deletions = old_products[old_products.isin(self.new_ids) == False]
                log.msg('INFO >>> Retry product deletions')
                for url in deletions['url']:
                    meta = {'check_options': False, 'dont_retry': True}
                    request = Request(url, callback=self.parse_product, meta=meta)
                    self._crawler.engine.crawl(request, self)

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "p02SgdLU"
        username = "biw"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        files = sftp.listdir_attr()

        last = get_last_file(self.file_start_with, files)

        sftp.get(last.filename, self.xls_file_path)

        # Convert XLXS file to CSV
        excel_to_csv(self.xls_file_path, self.csv_file_path)

        with open(self.csv_file_path) as f:
            reader = csv.DictReader(f, delimiter=',')
            for row in reader:
                if row['BI Brand'].upper() in self.brands:
                    continue
                self.brands.append(row['BI Brand'])

        for brand in self.brands:
            search_url = 'http://www.homedepot.com/s/%s?NCNI-5' % brand.replace('&', "AND").replace(' ', '+')
            yield Request(search_url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = response.xpath('//div[@id="products"]//div[@class="pod-plp__description"]/a/@href').extract()
        # listed colour options
        products += response.xpath('//div[@id="products"]//ul[contains(@class, "swatches__list")]//a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product, meta={'dont_retry': True})

        next_page = response.xpath('//a[@class="hd-pagination__link" and @title="Next"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[-1]))

        identifier = hxs.select('//span[@itemprop="productID"]/text()').extract()
        if identifier:
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        if response.status == 504 or response.status == 500 and response.meta.get('retry', 0)<3:
            port_number = re.findall(':\d+', response.url)
            if port_number:
                meta = response.meta.copy()
                meta['retry'] = meta.get('retry', 0) + 1
                new_url = re.sub(":\d+","", response.url)
                log.msg('ERROR >>> Redirect, port number in url : ' + new_url)
                yield Request(new_url, dont_filter=True, callback=self.parse_product, meta=meta)
                return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        identifier = hxs.select('//span[@itemprop="productID"]/text()').extract()

        if not identifier:
            request = self.retry(response, "ERROR >>> No identifier for product URL: " + response.url)
            if request:
                yield request
            return

        identifier = identifier[0]

        json_data = re.findall("PRODUCT_METADATA_JSON = (.*);", response.body)
        check_options = response.meta.get('check_options', True)
        if json_data and check_options:
            json_data = demjson.decode(json_data[0])['attributeDefinition']['attributeLookup']
            for value in json_data.values():
                option_url = response.url.replace(identifier, str(value))
                yield Request(option_url, callback=self.parse_product, meta={'check_options': False, 'dont_retry': True})

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price = hxs.select('//div[@class="pricingReg"]/span[@itemprop="price"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="ajaxPrice"]/text()').extract()

        price = price[0] if price else 0
        loader.add_value('price', price)
        loader.add_xpath('name', '//h1[@class="product-title__title"]/text()')
        image_url = hxs.select('//img[@id="mainImage"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        categories = []
        json_breadcrumb = re.findall("var BREADCRUMB_JSON = (.*);", response.body)
        if json_breadcrumb:
            json_breadcrumb = demjson.decode(json_breadcrumb[0])
            categories = json_breadcrumb['bcEnsightenData']['contentSubCategory'].split('>')
        loader.add_value('category', categories)

        brand = hxs.select('//h2[@itemprop="brand"]/text()').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)

        sku = response.xpath('//script/text()').re('"modelNumber":"(.+?)"')
        loader.add_value('sku', sku)

        if not loader.get_output_value('price') or 'OUT OF STOCK ONLINE' in response.body.upper():
            loader.add_value('stock', 0)

        item = loader.load_item()

        discontinued = hxs.select('//span[@class="discontinuedItem show"]')
        if discontinued:
            item['price'] = 0
            item['stock'] = 0

        if item['identifier']:
            self.new_ids.append(item['identifier'])
            yield item

    def parse_check_shipping(self, response):
        hxs = HtmlXPathSelector(response)

        item = response.meta['item']

        out_of_stock = hxs.select('//div[contains(@class, "error") and text()="Unavailable"]')
        if out_of_stock:
            item['stock'] = 0

        shipping_options = hxs.select('//a[@id="shipping_options_link"]')
        if shipping_options:
            shipping_url = 'http://origin.api.homedepot.com/wcs/resources/api/v1/tools/shipping?type=json&itemId=%s&quantity=1&price=%s&address=121'
            yield Request(shipping_url % (item['identifier'], item['price']), callback=self.parse_shipping_cost, meta={'item' : item})
        else:
            yield item

    def parse_shipping_cost(self, response):
        hxs = HtmlXPathSelector(response)

        item = response.meta['item']

        shipping_data = demjson.decode(response.body)
        if shipping_data:
            shipping_data = shipping_data['shippingResponse']['item']['shippingAndHandling']['shipmentType']['shipmentMode']
            if isinstance(shipping_data, list):
                # extract the highest shipping cost
                shipping = [extract_price(str(shipping['shipCharge'])) for shipping in shipping_data]
                shipping = shipping[0]
            else:
                shipping_data = demjson.decode(response.body)
                shipping = shipping_data['shippingResponse']['item']['shippingAndHandling']['shipmentType']['shipmentMode']['shipCharge']

            item['shipping_cost'] = str(shipping)

        yield item

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls'][0]
        else:
            url = response.request.url
        if retry < retries:
            log.msg(error)
            retry += 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=self.parse)


def get_last_file(start_with, files):
    """
    Returns the most recent file, for the file name which starts with start_with

    :param start_with: the file name has this form start_with + date
    :param files: files list sftp.listdir_attr
    """
    last = None
    for f in files:
        if ((last == None and start_with in f.filename and
             f.filename.endswith('.xlsx')) or
            (start_with in f.filename and f.filename.endswith('.xlsx') and
             f.st_mtime > last.st_mtime)):
            last = f
    return last

def excel_to_csv(xls_filename, csv_filename):
    wb = xlrd.open_workbook(xls_filename)
    sh = wb.sheet_by_index(0)
    csv_file = open(csv_filename, 'wb')
    wr = csv.writer(csv_file, quoting=csv.QUOTE_ALL)

    for rownum in xrange(sh.nrows):
        wr.writerow([unicode(val).encode('utf8') for val in sh.row_values(rownum)])

    csv_file.close()
