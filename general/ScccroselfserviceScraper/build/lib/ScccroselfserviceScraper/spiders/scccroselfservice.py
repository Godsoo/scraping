# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request, FormRequest
from ScccroselfserviceScraper.items import ScccroselfservicescraperItem
import re

class ScccroselfserviceSpider(scrapy.Spider):
    name = "scccroselfservice"
    start_urls = ['http://scccroselfservice.org/web/search/DOCSEARCH400S3']

    def parse(self, response):
        # first_date = '01/01/2010'
        # last_date = '03/02/2017'
        for y in range(2010, 2018):
            for m in range(1, 13):
                for d in range(1, 32):
                    if (y == 2017) and (m == 3) and (d > 2):
                        return
                    cur_date = str(m).zfill(2) + '/' + str(d).zfill(2) + '/' + str(y)
                    print cur_date
                    searchpost_payload = {
                                        'field_RecordingDateID-StartDate': cur_date,
                                        'field_RecordingDateID-EndDate': cur_date,
                                        'field_selfservice_documentTypes_shown': 'AMENDMENT/MODIFICATION+DEED+OF+TRUST,ASSIGNMENT+DEED+OF+TRUST,BOND+FOR+LOST+DEED+OF+TRUST,DECLARATION+OF+LOST+DEED+OF+TRUST,DEED,DEED+OF+TRUST,FICTITIOUS+DEED+OF+TRUST,REVOCABLE+TRANSFER+ON+DEATH+DEED,SHERIFFS+DEED+EXECUTION,SUPPLEMENT+DEED+TRUST,TRANSFER+ON+DEATH+DEED,TRUSTEES+DEED',
                                        'field_selfservice_documentTypes': 'AMDT,ASDT,BODT,DEDT,DEED,TRDE,FTDD,RTDD,SHDD,STDT,TODD,TEED'
                    }
                    yield FormRequest('http://scccroselfservice.org/web/searchPost/DOCSEARCH400S3', method='POST', formdata=searchpost_payload, headers={'X-Requested-With': 'XMLHttpRequest'}, callback=self.get_records)

    def get_records(self, response):
        trs = response.xpath('//table/tbody/tr')
        if len(trs) == 0:
            return

        # Getting 1 from http://scccroselfservice.org/web/searchResults/DOCSEARCH400S3?page=1
        page_num = re.search('page\=([\d]*)', response.url, re.M|re.I|re.S).group(1)
        if (page_num is None) or (page_num == ''):
            return

        for tr in trs:
            yield Request(response.urljoin(tr.xpath('@data-href').extract_first()), callback=self.parse_details)

        yield Request(re.sub('page\=[\d]+', 'page=' + str(int(page_num) + 1), response.url), callback=self.get_records)

    def parse_details(self, response):
        item = ScccroselfservicescraperItem()

        item['url'] = response.url        
        try:
            item['DocumentType'] = response.xpath('//ul/li[contains(text(), "Document Type")]/following-sibling::li/text()').extract_first().strip()
        except:
            item['DocumentType'] = ''
        try:
            item['DocumentNumber'] = response.xpath('//table//tr/td/div/strong[contains(text(), "Document Number:")]/../following-sibling::div/text()').extract_first().strip()
        except:
            item['DocumentNumber'] = ''
        try:
            item['RecordingDate'] = response.xpath('//table//tr/td/div/strong[contains(text(), "Recording Date:")]/../following-sibling::div/text()').extract_first().strip()
        except:
            item['RecordingDate'] = ''
        try:
            item['NumberPages'] = response.xpath('//table//tr/td/div/strong[contains(text(), "Number Pages:")]/../following-sibling::div/text()').extract_first().strip()
        except:
            item['NumberPages'] = ''
        try:
            item['Grantor'] = '|'.join([frag.strip() for frag in response.xpath('//table//tr/td/div/strong[contains(text(), "Grantor:")]/../following-sibling::div//text()').extract()])
        except:
            item['Grantor'] = ''
        try:
            item['Grantee'] = '|'.join([frag.strip() for frag in response.xpath('//table//tr/td/div/strong[contains(text(), "Grantee:")]/../following-sibling::div//text()').extract()])
        except:
            item['Grantee'] = ''
        try:
            item['APN'] = response.xpath('//table//tr/td/div/strong[contains(text(), "Assessor Parcel Number:")]/../following-sibling::div/text()').extract_first().strip()
        except:
            item['APN'] = ''
            
        yield item

