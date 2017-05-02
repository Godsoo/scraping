import os
import csv
import cStringIO
import imaplib
import email
import email.header

import re
import json
import urlparse
import xlrd
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider

from phantomjs import PhantomJS
import time

from scrapy import log


class TotalFeedSpider(BaseSpider):
    name = 'total_account-total-feed'
    allowed_domains = ['total.co.uk', 'hubtotal.net']
    start_urls = ('http://www.total.co.uk',)

    user_agent = 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/32.0.1700.107 Chrome/32.0.1700.107 Safari/537.36'

    def parse(self, response):
        # get the lastest link
        client = imaplib.IMAP4_SSL('imap.gmail.com', 993)
        client.login('totalfeedcompetitormonitor', 'uyWTStB6')
        client.select('INBOX')
        mails = client.uid('search', 'ALL')[1][0].split()[::-1]
        for mail_uid in mails:
            mail = client.uid('fetch', mail_uid, '(RFC822)')
            mail = email.message_from_string(mail[1][0][1])
            subject = email.header.decode_header(mail['Subject'])[0][0]
            if 'Nouveau message' not in subject:
                continue
            body = ' '.join([m.get_payload() for m in mail.get_payload()])
            url = re.search('(http.*?DownloadToken.*)', body).group(1).replace('\r', '')
            break


        browser = PhantomJS()
        # url = 'https://poseidon.hubtotal.net/zephyr/DownloadToken.jsp?token=iQ4rBu6SBKEB8KdOLpeO0JplfDhqJPqiIgOQrjsfuKedCnYC'
        self.log('>>> BROWSER: GET => %s' % url)
        browser.get(url)
        self.log('>>> BROWSER: OK')

        time.sleep(180)

        page_source = browser.driver.page_source

        browser.close()
        token = urlparse.parse_qs(urlparse.urlparse(url).query)['token'][0]

        hxs = HtmlXPathSelector(text=page_source)
        link_id = hxs.select('//h3[@class="unit-name"]/a/@id').re('file_(.*)')

        download_link = 'https://poseidon.hubtotal.net/zephyr/MFTWebAppDownloadToken/Download?file={}&token={}'.format(link_id[0], token)
        yield Request(download_link, callback=self.parse_feed)


    def parse_feed(self, response):
        f = cStringIO.StringIO(response.body)

        for row in self.excel_to_list(f.read()):
            log.msg(', '.join(row))
            loader = ProductLoader(item=Product(), selector=HtmlXPathSelector(text=''))
            identifier = '{}:{}'.format(row[0], row[1])
            loader.add_value('category', row[1])
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('name', identifier)
            loader.add_value('price', row[2])
            yield loader.load_item()



    def excel_to_list(self, xls_file):
        wb = xlrd.open_workbook(file_contents=xls_file)
        sh = wb.sheet_by_index(0)

        for rownum in xrange(1, sh.nrows):
            row = sh.row(rownum)
            yield (unicode(int(row[0].value)), unicode(row[1].value), unicode(row[2].value))

