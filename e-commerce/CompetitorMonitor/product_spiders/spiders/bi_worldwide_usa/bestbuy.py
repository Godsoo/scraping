# -*- coding: utf-8 -*-
"""
Customer: BIW USA
Website: http://www.bestbuy.com
Type: Marketplace, extract all dealers.
Crawling process: search by brand using the client file from the SFTP and extract all results
Options: extract all options
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4022-biw-usa-|-bestbuy-|-new-sites/details#

IMPORTANT! 

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
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter, url_query_parameter
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from scrapy.http import Request
from scrapy.item import Item, Field

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.config import DATA_DIR
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class BestBuyMeta(Item):
    warranty_price = Field()


class BestBuySpider(BaseSpider):
    name = 'biwusa-bestbuy.com'
    allowed_domains = ['bestbuy.com']
    start_urls = ('http://www.bestbuy.com',)
    errors = []

    brands = []

    file_start_with = 'BI USA File'

    xls_file_path = HERE + '/biw_products.xlsx'
    csv_file_path = HERE + '/biw_products.csv'

    options_identifiers = []

    def __init__(self, *args, **kwargs):
        super(BestBuySpider, self).__init__(*args, **kwargs)

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
                    request = Request(url, callback=self.parse_product)
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
            self.brands.sort()

        for brand in self.brands:
            log.msg('SEARCH BRAND >>> ' + brand)
            search_url = 'http://www.bestbuy.com/site/searchpage.jsp?st=%s&_dyncharset=UTF-8&id=pcat17071&type=page&sc=Global&cp=1&nrp=&sp=&qp=soldby_facet=Sold By~Best Buy^condition_facet=Condition~New&list=n&iht=y&usc=All+Categories&ks=960&keys=keys' % brand.replace('&', '%26').replace(' ', '+')
            yield Request(search_url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@class="list-item-info"]//h4/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next = hxs.select('//li[@class="pager-next"]/a/@href').extract()
        if next:
            current_page = int(url_query_parameter(response.url, 'cp', '0')) + 1
            next_page = add_or_replace_parameter(response.url, 'cp', str(current_page))
            yield Request(urljoin_rfc(base_url, next_page))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        options = hxs.select('//div[@class="variation-group"]//a/@href').extract()
        for option in options:
            option_url = urljoin_rfc(base_url, option)
            log.msg('INFO >>> OPTION FOUND: ' + option_url)
            yield Request(option_url, callback=self.parse_product)

        one_seller = hxs.select('//div[@class="marketplace-shipping-message"]//a[@class="bbypopup"]').extract()
        one_seller = True if one_seller else False

        identifier = hxs.select('//span[@itemprop="productID"]/text()').extract()

        if not identifier:
            request = self.retry(response, "ERROR >>> No identifier for product URL: " + response.url)
            if request:
                yield request
            return

        identifier = identifier[0]

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        price = ''.join(hxs.select('//div[@class="item-price"]/text()').extract()).strip()
        loader.add_value('price', price)
        loader.add_xpath('name', '//div[@itemprop="name"]/h1/text()')
        image_url = hxs.select('//meta[@property="og:image"]/@content').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        categories = hxs.select('//ol[@id="breadcrumb-list"]/li/a/text()').extract()[1:]
        loader.add_value('category', categories)

        brand = hxs.select('//div[@itemprop="brand"]/meta[@itemprop="name"]/@content').extract()
        brand = brand[0].strip() if brand else ''
        loader.add_value('brand', brand)

        sku = hxs.select('//span[@itemprop="model"]/text()').extract()
        sku = sku[0] if sku else ''
        loader.add_value('sku', sku)

        out_of_stock = hxs.select('//div[@class="cart-button" and @data-button-state-id="SOLD_OUT_ONLINE"]')
        if out_of_stock:
            loader.add_value('stock', 0)

        item = loader.load_item()

        warranty_price_url = response.url.partition('?')[0] + ';template=_protectionAndServicesTab'
        yield Request(warranty_price_url, callback=self.parse_warranty_price, meta={'item' : item, 'one_seller': one_seller})

    def parse_warranty_price(self, response):

        warranty_price = response.xpath('//td[@class="coverage-col term-price"]/text()').extract()
        if warranty_price:
            warranty_price = warranty_price[0].replace('$', '')
            item = response.meta.get('item')
            item['metadata'] = BestBuyMeta()
            item['metadata']['warranty_price'] = warranty_price
 
        dealers_url = response.url.partition(';')[0] + ';template=_buyingOptionsNewTab'
        yield Request(dealers_url, callback=self.parse_dealers, meta=response.meta)

    def parse_dealers(self, response):
        item = response.meta['item']

        try:
            hxs = HtmlXPathSelector(response)
            dealers = hxs.select('//div[@class="product-list" and @data-condition="new"]')
        except Exception:
            dealers = []

        if not dealers and response.meta['one_seller']:
            log.msg('ERROR >>> ONE SELLER: ' + item['url'])
            return

        for dealer in dealers:
            dealer_name = ''.join(dealer.select('.//div[@class="seller-name"]/span/text()').extract()).strip()
            if dealer_name.upper() == 'BEST BUY':
                log.msg('INFO >>> COLLECT BEST BUY ITEM: ' + item['url'])

                out_of_stock = dealer.select('.//div[@class="cart-button" and @data-button-state-id="SOLD_OUT_ONLINE"]')
                if out_of_stock:
                    item['stock'] = 0

                price = dealer.select('.//div[@class="medium-item-price"]//text()').extract()
                if not price:
                    log.msg('ADD TO CART PRICE >>> ' + item['url'])
                    price = dealer.select('@data-price').extract()
                item['price'] = extract_price(price[-1])
                shipping_cost = dealer.select('.//div[@class="shipping-cost-puck"]//text()').extract()
                if shipping_cost:
                    item['shipping_cost'] = extract_price(shipping_cost[0])
                break

        if item['identifier']:
            self.new_ids.append(item['identifier'])
            yield item

    def retry(self, response, error="", retries=3):
        meta = response.meta.copy()
        retry = int(meta.get('retry', 0))
        if 'redirect_urls' in meta and meta['redirect_urls']:
            url = meta['redirect_urls']
        else:
            url = response.request.url
        if retry < retries:
            log.msg(error)
            retry += 1
            meta['retry'] = retry
            meta['recache'] = True
            return Request(url, dont_filter=True, meta=meta, callback=response.request.callback)
                

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
