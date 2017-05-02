# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request
import re
from DocketsJustiaScraper import settings
import csv
import os

class JustiaSpider(scrapy.Spider):
    name = "justia"
    allowed_domains = ["dockets.justia.com", "docs.justia.com", "cases.justia.com"]
    start_urls = (
        'https://dockets.justia.com/',
    )

    def __init__(self, firstName="", lastName="", *args, **kwargs):
        super(JustiaSpider, self).__init__(*args, **kwargs)
        self.firstName = firstName
        self.lastName  = lastName
        self.name = (firstName + u' ' + lastName).replace(' ', '+').strip()
        search_url = 'https://dockets.justia.com/search?parties=%s&cases=mostrecent' % self.name
        self.start_urls = (search_url,)
        self.srno = 0
        self.max_party_name_num = 300
        self.max_party_attorney_num = 20
        self.csv_file_path = 'result.csv'
        self.partyTypeMatches = ['Plaintiff', 'Petitioner', 'Defendant', 'Respondent']
        self.myNone = 'N/A'
        self.new_file = True

    def parse(self, response):
        print( response.url )
        # cases = response.xpath('//div[@id="search-results"]//a[@class="case-name"]/strong/text()').extract()
        # cases = response.xpath('//div[@id="search-results"]//a[@class="case-name"]/strong/span/text()').extract()
        cases = response.xpath('//div[@id="search-results"]//a[@class="case-name"]/@href').extract()
        for case in cases:
            yield Request(url=response.urljoin(case), callback=self.parse_case)
        next_page = response.xpath('//div[@class="pagination to-large-font"]/a[contains(text(), "Next")]/@href').extract()
        if ( next_page ):
            yield Request(url=response.urljoin(next_page[0]), callback=self.parse)


    def parse_case(self, response):
        self.srno = self.srno + 1

        caseName = response.xpath('//div[@class="title-wrapper"]/h1/text()').extract()
        caseName = caseName[0].strip() if caseName else self.myNone

        partyFirstType = ''
        partySecondType = ''
        partyFirstNames = []
        partySecondNames = []
        partyTypes = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Plaintiff") or contains(text(), "Petitioner") or contains(text(), "Defendant") or contains(text(), "Respondent")]')
        if ( len(partyTypes) == 2 ):
            partyFirstType = partyTypes.xpath('text()').extract()[0].strip()
            partyFirstNames = partyTypes[0].xpath('../following-sibling::span/text()').extract()[0].split(',')
            partySecondType = partyTypes.xpath('text()').extract()[1].strip()
            partySecondNames = partyTypes[1].xpath('../following-sibling::span/text()').extract()[0].split(',')
        elif ( len(partyTypes) == 1 ):
            partyFirstType = partyTypes.xpath('text()').extract()[0].strip()
            partyFirstNames = partyTypes[0].xpath('../following-sibling::span/text()').extract()[0].split(',')

        partyFirstType = partyFirstType.replace('Petitioner', 'Plaintiff')
        partyFirstType = partyFirstType.replace('Respondent', 'Defendant')
        partyFirstType = partyFirstType.replace(':', '')
        partySecondType = partySecondType.replace('Petitioner', 'Plaintiff')
        partySecondType = partySecondType.replace('Respondent', 'Defendant')
        partySecondType = partySecondType.replace(':', '')

        if ( len(partyFirstNames) > 0 ):
            partyFirstRange = '%d ~ %d' % (1, len(partyFirstNames))
        else:
            partyFirstRange = self.myNone
        if ( len(partySecondNames) > 0 ):
            partySecondRange = '%d ~ %d' % (len(partyFirstNames) + 1, len(partyFirstNames) + len(partySecondNames))
        else:
            partySecondRange = self.myNone

        caseNum = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Case Number:")]')
        caseNum = caseNum.xpath('../following-sibling::span/text()').extract()[0].strip() if caseNum else self.myNone

        filingDate = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Filed:")]')
        filingDate = filingDate.xpath('../following-sibling::span/text()').extract()[0].strip() if filingDate else self.myNone

        courtName = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Court:")]')
        courtName = courtName.xpath('../following-sibling::span/text()').extract()[0].strip() if courtName else self.myNone

        office = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Office:")]')
        office = office.xpath('../following-sibling::span/text()').extract()[0].strip() if office else self.myNone

        county = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "County:")]')
        county = county.xpath('../following-sibling::span/text()').extract()[0].strip() if county else self.myNone

        appearancejudge = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Presiding Judge:")]')
        appearancejudge = appearancejudge.xpath('../following-sibling::span/text()').extract()[0].strip() if appearancejudge else self.myNone

        caseType = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Nature of Suit:")]')
        caseType = caseType.xpath('../following-sibling::span/text()').extract()[0].strip() if caseType else self.myNone

        category = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Cause of Action:")]')
        category = category.xpath('../following-sibling::span/text()').extract()[0].strip() if category else self.myNone

        jury = response.xpath('//div[@id="case-info-table"]/div[@class="row"]/span/strong[contains(text(), "Jury Demanded By:")]')
        jury = jury.xpath('../following-sibling::span/text()').extract()[0].strip() if jury else self.myNone

        originalRecord = response.xpath('//div[@id="document-list-documents"]/table//tr[contains(@id, "document")]')
        if ( originalRecord ):
            originalRecord_date = originalRecord.xpath('td[1]/text()').extract()
            originalRecord_date = originalRecord_date[0].strip() if originalRecord_date else self.myNone
            originalRecord_number = originalRecord.xpath('td[2]/strong/a/text()').extract()
            originalRecord_number = originalRecord_number[0].strip() if originalRecord_number else self.myNone
            originalRecord_link = originalRecord.xpath('td[2]/strong/a/@href').extract()
            originalRecord_link = originalRecord_link[0].strip() if originalRecord_link else self.myNone
            originalRecord_content = ''
            originalRecord_content_q = originalRecord.xpath('td[3]/text()').extract()
            for content in originalRecord_content_q:
                originalRecord_content = originalRecord_content + content.strip()
            if (originalRecord_content == ''):
                originalRecord_content = self.myNone
        else:
            originalRecord_date = self.myNone
            originalRecord_number = self.myNone
            originalRecord_link = self.myNone
            originalRecord_content = self.myNone

        party_attorney_names = []
        party_attorneies = response.xpath('//div[@id="party-searches"]/table//tr/td[contains(text(), "Represented By:")]')
        for party_attorney in party_attorneies:
            party_attorney_name = party_attorney.xpath('following-sibling::td/a/text()').extract()
            party_attorney_name = party_attorney_name[0] if party_attorney_name else self.myNone
            party_attorney_name = re.sub(r'\(.*\)', '', party_attorney_name)
            if ( (party_attorney_name != self.myNone) and (party_attorney_name not in party_attorney_names) ):
                party_attorney_names.append(party_attorney_name)

        item = ['Sr.No', self.srno, 'caseName', caseName, 'partyFirstType', partyFirstType, 'partyFirstRange', partyFirstRange, 'partySecondType', partySecondType, 'partySecondRange', partySecondRange]

        party_name_counter = 0
        for partyfirstname in partyFirstNames:
            party_name_counter = party_name_counter + 1
            item.append('party(%d).name' % party_name_counter)
            item.append(partyfirstname.strip())
        for partysecondname in partySecondNames:
            party_name_counter = party_name_counter + 1
            item.append('party(%d).name' % party_name_counter)
            item.append(partysecondname.strip())
        for i in range(party_name_counter + 1, self.max_party_name_num):
            item.append('party(%d).name' % i)
            item.append(self.myNone)

        item.append('caseNum')
        item.append(caseNum)
        item.append('filingDate')
        item.append(filingDate)
        item.append('courtName')
        item.append(courtName)
        item.append('office')
        item.append(office)
        item.append('county')
        item.append(county)
        item.append('appearance.judge')
        item.append(appearancejudge)
        item.append('caseType')
        item.append(caseType)
        item.append('category')
        item.append(category)
        item.append('jury')
        item.append(jury)
        item.append('originalRecord.date')
        item.append(originalRecord_date)
        item.append('originalRecord.number')
        item.append(originalRecord_number)
        item.append('originalRecord.link')
        item.append(originalRecord_link)
        item.append('originalRecord.content')
        item.append(originalRecord_content)

        party_attorney_counter = 0
        for party_attorney_name in party_attorney_names:
            party_attorney_counter = party_attorney_counter + 1
            item.append('party.attorney(%d).name' % party_attorney_counter)
            item.append(party_attorney_name.strip())
        for i in range(party_attorney_counter + 1, self.max_party_attorney_num):
            item.append('party.attorney(%d).name' % i)
            item.append(self.myNone)

        # write_to_csv( item )
        #################################### writing to csv ##############################

        keys = []
        values = []
        for i, kv in enumerate(item):
            if i % 2 == 0:
                keys.append( re.sub(r'In Re:', '', str(kv).strip()) )
            else:
                values.append( re.sub(r'In Re:', '', str(kv).strip()) )
        if ( self.new_file ):
            writer = csv.writer(open(settings.csv_file_path, 'w'), lineterminator='\n')
            writer.writerow(keys)
            self.new_file = False
        else:
            writer = csv.writer(open(settings.csv_file_path, 'a'), lineterminator='\n')
        writer.writerow(values)
        
        ################################# saving pdf ####################################

        if ( originalRecord_link != self.myNone ):
            req = Request(url=originalRecord_link, callback=self.parse_content)
            req.meta['filename'] = caseName + '.pdf'
            yield req

    def parse_content(self, response):
        pdf_url = response.xpath('//a[@class="pdf-icon pull-right"]/@href').extract()
        pdf_url = pdf_url[0] if pdf_url else self.myNone
        if ( pdf_url != self.myNone ):
            yield Request(url=pdf_url, callback=self.save_pdf, meta=response.meta)

    def save_pdf(self, response):
        with open(settings.pdf_file_path + response.meta['filename'], 'wb') as f:
            f.write(response.body)



