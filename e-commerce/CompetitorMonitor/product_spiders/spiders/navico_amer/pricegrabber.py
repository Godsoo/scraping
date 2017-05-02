"""
Name: navico-amer-pricegrabber.com
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
Ticket reference: https://www.assembla.com/spaces/competitormonitor/tickets/4213

IMPORTANT:

- Use "dont_filter=True" on first request.
  This must be that way because the website redirect to the same url sometimes.
"""

import os
import csv

import paramiko
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT

HERE = os.path.abspath(os.path.dirname(__file__))


class PriceGrabberSpider(BaseSpider):
    name = 'navico-amer-pricegrabber.com'
    allowed_domains = ['pricegrabber.com']
    start_urls = ['http://www.pricegrabber.com/']

    user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0'

    def start_requests(self):
        transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))
        password = "A7Ct8rLX07n"
        username = "navico"
        transport.connect(username = username, password = password)
        sftp = paramiko.SFTPClient.from_transport(transport)

        csv_file = os.path.join(HERE, 'navico_feed_pricegrabber.csv')

        sftp.get('navico_feed_amer.csv', csv_file)

        with open(csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                item = {
                    'sku': row['Product.BaseSKU'],
                    'brand': row.get('Brand.CUST', '')
                }
                url = 'http://www.pricegrabber.com/%s-products/1/' % item['sku'].replace('-', '')
                yield Request(url, meta={'search_item': item}, dont_filter=True)

        remote_filename = 'navico_screensize_products.csv'
        csv_file = os.path.join(HERE, 'navico_screensize_products_pricegrabber.csv')

        sftp.get(remote_filename, csv_file)

        with open(csv_file) as f:
            reader = csv.DictReader(f, delimiter=',')
            for i, row in enumerate(reader, 1):
                item = {
                    'sku': row['Manufacturer Part Number'],
                    'brand': row['Brand']
                }
                url = 'http://www.pricegrabber.com/%s-products/1/' % item['sku'].replace('-', '')
                yield Request(url, meta={'search_item': item}, dont_filter=True)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//div[@id="product_results"]/div[contains(@class, "product_item")]'
                              '//div[contains(@class, "moreLinks")]/a[contains(@class, "more-link")]/@href')\
                      .extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url),
                          meta={'search_item': response.meta['search_item']},
                          callback=self.parse_product)

        next_page = hxs.select('//div[@id="pagination"]//li[@class="next"]'
                               '/a[not(contains(@class, "off"))]/@href').extract()
        for url in next_page:
            yield Request(urljoin_rfc(base_url, url),
                          meta={'search_item': response.meta['search_item']},
                          callback=self.parse_product)

        if (not hxs.select('//*[@id="search_no_results"]')) and (not products):
            for item in self.parse_product(response):
                yield item

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        try:
            master_id = response.xpath('//script/text()').re('masterid":"(.+?)"')[0]
        except IndexError:
            retry_no = int(response.meta.get('retry_no', 0))
            if retry_no < 10:
                retry_no += 1
                yield Request(response.url,
                              meta={'search_item': response.meta['search_item'],
                                    'retry_no': retry_no},
                              callback=self.parse_product,
                              dont_filter=True)
            return

        categories = filter(lambda s: bool(s),
            map(unicode.strip,
                hxs.select('//div[@id="breadcrumbs"]//li/a/text()').extract()))

        sellers = hxs.select('//table[@id="price_grid"]//tr[contains(@class, "retid_")]')
        for seller_details_xs in sellers:
            seller_id = seller_details_xs.select('@class').re(r'retid_(\d+)')[0]
            seller_name = filter(lambda s: bool(s.strip()), seller_details_xs\
                .select('.//div[@class="merchant"]//@alt|//div[@class="merchant"]/a/text()')\
                .extract())[0]
            loader = ProductLoader(item=Product(), selector=seller_details_xs)
            loader.add_value('identifier', '%s:%s' % (master_id, seller_id))
            loader.add_xpath('name', '//*[@id="product_title"]/text()')
            loader.add_value('url', response.url)
            loader.add_xpath('sku', '//*[@id="product_mpn"]/text()', re=r'MPN: (.*)')
            loader.add_value('category', categories)
            loader.add_xpath('image_url', '//div[@id="product_image_section"]//img/@src')
            loader.add_xpath('price', './/div[@class="price"]//text()', re=r'[\d,.]+')
            loader.add_value('brand', response.meta['search_item']['brand'].strip())
            loader.add_value('dealer', seller_name)
            yield loader.load_item()
