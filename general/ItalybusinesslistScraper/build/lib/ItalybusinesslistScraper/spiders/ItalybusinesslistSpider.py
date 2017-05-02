# -*- coding: utf-8 -*-
import scrapy
import requests
from scrapy.selector import Selector
from scrapy.http import Request
import re
from ItalybusinesslistScraper.items import CompanyItem

class ItalybusinesslistSpider(scrapy.Spider):
    name = "italybusinesslist"
    start_urls = [
        # 'http://italybusinesslist.com/',
        'http://italybusinesslist.com/companies/1603/', # List-1
        'http://italybusinesslist.com/companies/2329/', # List-2
        'http://italybusinesslist.com/companies/031/',  # List-3
        'http://italybusinesslist.com/companies/1314/', # List-4
        'http://italybusinesslist.com/companies/2135/', # List-5
        'http://italybusinesslist.com/companies/1351/', # List-6
        'http://italybusinesslist.com/companies/2152/', # List-7
    ]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, callback=self.get_PageUrls)
            # break

    def get_PageUrls(self, response):
        for page_url in response.xpath('//select[@name="select"]/option/@value').extract():
            yield Request(url=response.urljoin(page_url), callback=self.get_CompanyUrls)
            # break

    def get_CompanyUrls(self, response):
        for company_url in response.xpath('//ul[@class="browse-category"]/div[@class="entry-body"]/h4/a/@href').extract():
            yield Request(url=response.urljoin(company_url), callback=self.parse_CompanyInfo)
            # break
      
    def parse_CompanyInfo(self, response):
        print(response.url)
        item = CompanyItem()

        item['TELEFONO'] = response.xpath('//div[@id="content_overview"]//meta[@itemprop="telephone"]/@content').extract_first()
        item['FAX'] = response.xpath('//div[@id="content_overview"]//meta[@itemprop="faxNumber"]/@content').extract_first()
        item['EMAIL'] = response.xpath('//div[@id="content_overview"]//address[@class="email"]/text()').extract_first()
        item['RAGIONE_SOCIALE'] = response.xpath('//div[@id="content_overview"]//h1[@itemprop="name"]/a/text()').extract_first()
        item['INDIRIZZO'] = response.xpath('//div[@id="content_overview"]//span[@itemprop="streetAddress"]/text()').extract_first()

        if (item['TELEFONO'] is None):
            item['TELEFONO'] = ''
        if (item['FAX'] is None):
            item['FAX'] = ''
        if (item['EMAIL'] is None):
            item['EMAIL'] = ''
        if (item['RAGIONE_SOCIALE'] is None):
            item['RAGIONE_SOCIALE'] = ''
        if (item['INDIRIZZO'] is None):
            item['INDIRIZZO'] = ''

        item['ADDRESS'] = re.sub('\s+', ' ', ' '.join(response.xpath('//div[@id="content_overview"]//address[@itemprop="address"]/text()').extract()))
        try:
            item['CAP'] = re.search('([0-9]{5})', ' '.join(response.xpath('//div[@id="content_overview"]//address[@itemprop="address"]//text()').extract()), re.I|re.M|re.S).group(1)
        except:
            item['CAP'] = ''

        yield item
