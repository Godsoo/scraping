# -*- coding: utf-8 -*-
import scrapy
import requests
from scrapy.selector import Selector
from scrapy.http import Request
import re
from CercaziendeScraper.items import CompanyItem

class CercaziendeSpider(scrapy.Spider):
    name = "CercaziendeSpider"
    # allowed_domains = ["cercaziende.it"]
    start_urls = [
        'http://www.cercaziende.it/',
        # ('http://www.cercaziende.it/italy/it_IT/search.htm?keywords=%s&where=&submitbutton=Cerca&ca_left=&placename=&categoryname=&placeid=' % s) for s in 'abcdefghijklmnopqrstuvwxyz'
        # 'http://www.cercaziende.it/italy/it_IT/search.htm?keywords=a&where=&submitbutton=Cerca&ca_left=&placename=&categoryname=&placeid=',
        # 'http://www.cercaziende.it/italy/it_IT/search.htm?keywords=b&where=&submitbutton=Cerca&ca_left=&placename=&categoryname=&placeid=',
    ]

    def __init__(self):
        self.breadcrumb_queue = []
        self.breadcrumb_appeared = []

    # def start_requests(self):
    #     for url in self.start_urls:
    #         yield Request(url=url, callback=self.get_CompanyUrls)

    # def parse_from_category_part(self, response):
    def parse(self, response):
        category_urls = response.xpath('//div[@class="container home-sec categories-go"]/div[@class="col-md-3 cat-footer"]/h3/a/@href').extract()
        # self.logger.info(category_urls)
        for category_url in category_urls:
            # self.logger.info(category_url)
            yield Request(url=response.urljoin(category_url), callback=self.get_CompanyUrls)
            # break

        scan_search_urls = [('http://www.cercaziende.it/italy/it_IT/search.htm?keywords=%s&where=&submitbutton=Cerca&ca_left=&placename=&categoryname=&placeid=' % s) for s in 'abcdefghijklmnopqrstuvwxyz']
        for scan_url in scan_search_urls:
            yield Request(url=scan_url, callback=self.get_CompanyUrls)

        if (len(self.breadcrumb_queue) > 0):
            yield Request(url=response.urljoin(self.breadcrumb_queue.pop()), callback=self.get_CompanyUrls)

    def get_CompanyUrls(self, response):
    # def parse(self, response):
        page_num = 1
        req_params = response.url.split('?')[1]

        try:
            keywords = re.search('keywords\=([\w\s]+)?[\&]?', req_params, re.I|re.M|re.S).group(1)
        except:
            keywords = ''
        try:
            ca_left = re.search('ca_left\=([\w\s]+)?[\&]?', req_params, re.I|re.M|re.S).group(1)
        except:
            ca_left = ''
        try:
            where = re.search('where\=([\w\s]+)?[\&]?', req_params, re.I|re.M|re.S).group(1)
        except:
            where = ''
        try:
            placename = re.search('placename\=([\w\s]+)?[\&]?', req_params, re.I|re.M|re.S).group(1)
        except:
            placename = ''

        payload = { 'keywords': keywords if keywords else '',
                    'where': where if where else '',
                    'ca_left': ca_left if ca_left else '',
                    'placename': placename if placename else '',
                    'page': '1',
                    'addPage': 'false' }

        res_page = response
        # self.logger.info(req_params)
        # self.logger.info(payload)
        while (1):
            try:
                company_urls = res_page.xpath('//div[@class="result_sx"]//div[@class="annuncio_foto"]/a/@href').extract()
                # self.logger.info(company_urls)
                if ( len(company_urls) == 0 ):
                    break
                for company_url in company_urls:
                    yield Request(url=response.urljoin(company_url), callback=self.parse_CompanyInfo)
                # break
                page_num = page_num + 1
                payload['page'] = str(page_num)
                res_page = Selector(requests.post( url='http://www.cercaziende.it/italy/it_IT/core/search/searchresults',
                                                  data=payload, headers={'X-Requested-With': 'XMLHttpRequest'}))
            except:
                break

        if (len(self.breadcrumb_queue) > 0):
            yield Request(url=response.urljoin(self.breadcrumb_queue.pop()), callback=self.get_CompanyUrls)

    def parse_CompanyInfo(self, response):

        breadcrumbs = response.xpath('//ol[@class="breadcrumb-container"]/li/a[@property="item"]/@href').extract()
        for bc in breadcrumbs:
            if (bc not in self.breadcrumb_appeared):
                self.breadcrumb_queue.append(bc)
                self.breadcrumb_appeared.append(bc)

        contact_form = response.xpath('//div[@class="row wrapper-content-minisite artic go-contatti"]/div[@class="col-md-6"]')

        # Via Sidney Sonnino, Cagliari, Italia
        # Via Dei Maceri, Bologna
        # -, 86079 Venafro, Italia 
        # Via Tricino, 45, 84018 Scafati, Italia
        # Via Mazzini, 37, 26013 Crema, Italia
        # Via Capellini, 82019, Sant'agata Dei Goti, Benevento
        address = contact_form.xpath('div/div/div/h2[@class="ex_h3 address"]/text()').extract_first().strip()
        address = address.replace(', Italia', '')
        if (re.search('[0-9]{5}', address, re.M|re.S|re.I)):
            address = re.search('([\w\s]*)?[\,0-9\s]*([0-9]{5})[\,\s]?([\w\s\']*)?[\,\s]?([\w\s]*)', address, re.M|re.S|re.I)
        else:
            address = re.search('([\w\s]*)?[\,0-9\s]*([0-9]{5})?[\,\s]?([\w\s\']*)?[\,\s]?([\w\s]*)', address, re.M|re.S|re.I)

        item = CompanyItem()

        item['CATEGORIA'] = contact_form.xpath('div/div/div/h2[@class="ex_h3 category_style"]/text()').extract_first().strip()
        if (item['CATEGORIA'] is None):
            item['CATEGORIA'] = ''

        item['RAGIONE_SOCIALE'] = contact_form.xpath('div/h3/text()').extract_first().replace('Contatta', '').strip()
        if (item['RAGIONE_SOCIALE'] is None):
            item['RAGIONE_SOCIALE'] = ''

        try:
            item['INDIRIZZO'] = address.group(1).strip()
        except:
            item['INDIRIZZO'] = ''
        try:
            item['CAP'] = address.group(2).strip()
            if (item['CAP'] is None):
                item['CAP'] = ''
        except:
            item['CAP'] = ''
        try:
            item['COMUNE'] = address.group(3).strip()
        except:
            item['COMUNE'] = ''
        try:
            item['PROVINCIA'] = address.group(4).strip()
        except:
            item['PROVINCIA'] = ''

        if (item['PROVINCIA'] == ''):
            item['PROVINCIA'] = item['COMUNE']
            item['COMUNE'] = ''

        item['TELEFONO'] = contact_form.xpath('.//div[contains(@id, "contactvalue") and contains(@id, "telephone")]/h4/text()').extract_first()
        if (item['TELEFONO'] is None):
            item['TELEFONO'] = ''
        item['FAX'] = contact_form.xpath('.//div[contains(@id, "contactvalue") and contains(@id, "fax")]/h4/text()').extract_first()
        if (item['FAX'] is None):
            item['FAX'] = ''
        item['EMAIL'] = contact_form.xpath('.//div[contains(@id, "contactvalue") and contains(@id, "email")]/h4/a/text()').extract_first()
        if (item['EMAIL'] is None):
            item['EMAIL'] = ''
        item['WEBSITE'] = contact_form.xpath('.//div[contains(@id, "contactvalue") and contains(@id, "website")]/h4/a/@href').extract_first()
        if (item['WEBSITE'] is None):
            item['WEBSITE'] = ''

        yield item

        if (len(self.breadcrumb_queue) > 0):
            yield Request(url=response.urljoin(self.breadcrumb_queue.pop()), callback=self.get_CompanyUrls)
