# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request, FormRequest
from HpdonlineScraper.items import HpdonlinescraperItem
import csv
import time

def ExtractAllText(tag):
    return ''.join([frag.strip() for frag in tag.xpath('.//text()').extract()]).strip()

class HpdonlineSpider(scrapy.Spider):
    name = "hpdonline"
    start_urls = ['https://hpdonline.hpdnyc.org/HPDonline/provide_address.aspx']

    def __init__(self):
        self.address_list = [   {'Borough': 'BK', 'Number': '302',    'Street': 'BEVERLEY ROAD'},
                                {'Borough': 'BK', 'Number': '44',     'Street': 'Morgan Avenue'},   
                                {'Borough': 'BK', 'Number': '2178',   'Street': 'BERGEN AVENUE'},
                                {'Borough': 'BK', 'Number': '1',      'Street': '1 PLACE'},
                                {'Borough': 'QN', 'Number': '42736',  'Street': '54 AVENUE'},
                                {'Borough': 'QN', 'Number': '1-014A', 'Street': '115 STREET'} 
                                ]
        self.address_index = 0
        self.post_first = 'https://hpdonline.hpdnyc.org/HPDonline/provide_address.aspx'

    def parse(self, response):

        print len(self.address_list)
        if self.address_index >= len(self.address_list):
            return
        # Borough # 'BK': 'Brooklyn' -> 3, 'QN': 'Queens' -> 4
        # post_first = 'https://hpdonline.hpdnyc.org/HPDonline/provide_address.aspx'

        EVENTTARGET = response.xpath('//input[@id="__EVENTTARGET"]/@value').extract_first()
        EVENTARGUMENT = response.xpath('//input[@id="__EVENTARGUMENT"]/@value').extract_first()
        LASTFOCUS = response.xpath('//input[@id="__LASTFOCUS"]/@value').extract_first()
        hf_phn = response.xpath('//input[@id="hf_phn"]/@value').extract_first()
        hf_street = response.xpath('//input[@id="hf_street"]/@value').extract_first()
        hf_boro = response.xpath('//input[@id="hf_boro"]/@value').extract_first()
        hf_UserStatus = response.xpath('//input[@id="hf_UserStatus"]/@value').extract_first()
        mymaintable_hf_UserStatus = response.xpath('//input[@id="mymaintable_hf_UserStatus"]/@value').extract_first()

        payload_first = {   '__EVENTTARGET': EVENTTARGET if EVENTTARGET else '',
                            '__EVENTARGUMENT': EVENTARGUMENT if EVENTARGUMENT else '',
                            '__LASTFOCUS': LASTFOCUS if LASTFOCUS else '',
                            '__VIEWSTATE': response.xpath('//input[@id="__VIEWSTATE"]/@value').extract_first(),
                            '__VIEWSTATEGENERATOR': response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').extract_first(),
                            '__EVENTVALIDATION': response.xpath('//input[@id="__EVENTVALIDATION"]/@value').extract_first(),
                            'mymaintable:ddlServices': '0',
                            'mymaintable:hf_UserStatus': mymaintable_hf_UserStatus if mymaintable_hf_UserStatus else '',
                            'ddlBoro': '3',
                            'txtHouseNo': '44',
                            'txtStreet': 'Morgan+Avenue',
                            'btnSearch': 'Search',
                            'RadioStrOrBlk': 'Street',
                            'hf_phn': hf_phn if hf_phn else '',
                            'hf_street': hf_street if hf_street else '',
                            'hf_boro': hf_boro if hf_boro else '',
                            'hf_UserStatus': hf_UserStatus if hf_UserStatus else '' }

        # with open('address_temp.csv', 'r') as f:
        #     content = csv.reader(f)
        #     for index, address in enumerate(content):
        #         if index == 0:
        #             continue
        #         # print address[0], address[1], address[2]
        #         payload_first['ddlBoro'] = '3' if address[0] == 'BK' else '4'
        #         payload_first['txtHouseNo'] = address[1]
        #         payload_first['txtStreet'] = address[2]
        #         # print(payload_first)
        #         yield FormRequest(url=self.post_first, method='POST', formdata=payload_first, callback=self.parse_first)

        address = self.address_list[self.address_index]
        payload_first['ddlBoro'] = '3' if address['Borough'] == 'BK' else '4'
        payload_first['txtHouseNo'] = address['Number']
        payload_first['txtStreet'] = address['Street']
        print self.address_index
        print address
        yield FormRequest(url=self.post_first, method='POST', formdata=payload_first, callback=self.parse_first, meta={'address': address}, dont_filter=True)
        self.address_index = self.address_index + 1
        # for address in self.address_list:
        #     payload_first['ddlBoro'] = '3' if address['Borough'] == 'BK' else '4'
        #     payload_first['txtHouseNo'] = address['Number']
        #     payload_first['txtStreet'] = address['Street']

        #     # time.sleep(10)
        #     # print (payload_first)
        #     yield FormRequest(url=self.post_first, method='POST', formdata=payload_first, callback=self.parse_first, meta={'address': address})

    def parse_first(self, response):
        if (len(response.xpath('//table[@id="mymaintable_BldgInfo"]/tr')) == 0):
            yield Request(url=self.post_first, callback=self.parse, dont_filter=True)
            return
        item = HpdonlinescraperItem()

        item['Owner'] = ''
        item['LastReg'] = ''
        item['RegExp'] = ''
        item['Organization'] = ''
        item['LastNm'] = ''
        item['FirstNm'] = ''
        item['HouseNo'] = ''
        item['StreetNm'] = ''
        item['Apt'] = ''
        item['City'] = ''
        item['State'] = ''
        item['Zip'] = ''

        HPD1 = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblBldgid"]/text()').extract_first()
        HPD2 = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblStatus"]/text()').extract_first()
        if (not HPD1):
            HPD1 = ''
        if (not HPD2):
            HPD2 = ''
        item['HPDsharp'] = (HPD1 + ' ' + HPD2).strip()
        item['Range'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblhn"]/text()').extract_first()
        item['Block'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblBlock"]/text()').extract_first()
        item['Lot'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblLot"]/text()').extract_first()
        item['CD'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblCD"]/text()').extract_first()
        item['CensusTract'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblCnsus"]/text()').extract_first()
        item['Stories'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblstry"]/text()').extract_first()
        item['A_Units'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblA"]/text()').extract_first()
        item['B_Units'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblB"]/text()').extract_first()
        item['Ownership'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblShort"]/text()').extract_first()
        item['Registrationsharp'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblMDR"]/text()').extract_first()
        item['Class'] = response.xpath('//table[@id="mymaintable_BldgInfo"]/tr/td/span[@id="mymaintable_lblcls"]/text()').extract_first()

        yield item

        post_second = 'https://hpdonline.hpdnyc.org/HPDonline/select_application.aspx'

        EVENTTARGET = response.xpath('//input[@id="__EVENTTARGET"]/@value').extract_first()
        EVENTARGUMENT = response.xpath('//input[@id="__EVENTARGUMENT"]/@value').extract_first()
        LASTFOCUS = response.xpath('//input[@id="__LASTFOCUS"]/@value').extract_first()
        hf_UserStatus = response.xpath('//input[@id="hf_UserStatus"]/@value').extract_first()
        mymaintable_hf_UserStatus = response.xpath('//input[@id="mymaintable_hf_UserStatus"]/@value').extract_first()
        server = response.xpath('//input[@id="server"]/@value').extract_first()
        hf_boronum = response.xpath('//input[@id="hf_boronum"]/@value').extract_first()
        hf_server = response.xpath('//input[@id="hf_server"]/@value').extract_first()
        hf_classI = response.xpath('//input[@id="hf_classI"]/@value').extract_first()
        Corp = response.xpath('//input[@id="Corp"]/@value').extract_first()
        hf_PayTotal = response.xpath('//input[@id="hf_PayTotal"]/@value').extract_first()
        hf_Transmitted = response.xpath('//input[@id="hf_Transmitted"]/@value').extract_first()
        hf_InvcTotal = response.xpath('//input[@id="hf_InvcTotal"]/@value').extract_first()
        hf_MapUrl = response.xpath('//input[@id="hf_MapUrl"]/@value').extract_first()
        hf_classA = response.xpath('//input[@id="hf_classA"]/@value').extract_first()
        hf_classB = response.xpath('//input[@id="hf_classB"]/@value').extract_first()
        hf_classC = response.xpath('//input[@id="hf_classC"]/@value').extract_first()
        hf_boro = response.xpath('//input[@id="hf_boro"]/@value').extract_first()
        hf_QueryMessage = response.xpath('//input[@id="hf_QueryMessage"]/@value').extract_first()
        hf_PhoneNumber = response.xpath('//input[@id="hf_PhoneNumber"]/@value').extract_first()

        payload = {     '__EVENTTARGET': 'lbtnRegistration', # EVENTTARGET if EVENTTARGET else '',
                        '__EVENTARGUMENT': EVENTARGUMENT if EVENTARGUMENT else '',
                        '__LASTFOCUS': LASTFOCUS if LASTFOCUS else '',
                        '__VIEWSTATE': response.xpath('//input[@id="__VIEWSTATE"]/@value').extract_first(),
                        '__VIEWSTATEGENERATOR': response.xpath('//input[@id="__VIEWSTATEGENERATOR"]/@value').extract_first(),
                        '__EVENTVALIDATION': response.xpath('//input[@id="__EVENTVALIDATION"]/@value').extract_first(),
                        'mymaintable:ddlServices': '0',
                        'mymaintable:hf_UserStatus': mymaintable_hf_UserStatus if mymaintable_hf_UserStatus else '',
                        'server': server if server else '',
                        'hf_boronum': hf_boronum if hf_boronum else '',
                        'hf_report_name': response.xpath('//input[@id="hf_report_name"]/@value').extract_first(),
                        'hf_server': hf_server if hf_server else '',
                        'hf_classI': hf_classI if hf_classI else '',
                        'Corp': Corp if Corp else '',
                        'hf_PayTotal': hf_PayTotal if hf_PayTotal else '',
                        'hf_Transmitted': hf_Transmitted if hf_Transmitted else '',
                        'hf_InvcTotal': hf_InvcTotal if hf_InvcTotal else '',
                        'hf_MapUrl': hf_MapUrl if hf_MapUrl else '',
                        'hf_classA': hf_classA if hf_classA else '',
                        'hf_classB': hf_classB if hf_classB else '',
                        'hf_classC': hf_classC if hf_classC else '',
                        'hf_boro': hf_boro if hf_boro else '',
                        'hf_QueryMessage': hf_QueryMessage if hf_QueryMessage else '',
                        'hf_PhoneNumber': hf_PhoneNumber if hf_PhoneNumber else '',
                        'hf_Spanish': response.xpath('//input[@id="hf_Spanish"]/@value').extract_first() }

        # print (payload)
        yield FormRequest(url=post_second, method='POST', formdata=payload, callback=self.parse_second, meta={'item': item}, dont_filter=True)

    def parse_second(self, response):
        item = response.meta['item']

        item['HPDsharp'] = ''
        item['Range'] = ''
        item['Block'] = ''
        item['Lot'] = ''
        item['CD'] = ''
        item['CensusTract'] = ''
        item['Stories'] = ''
        item['A_Units'] = ''
        item['B_Units'] = ''
        item['Ownership'] = ''
        item['Registrationsharp'] = ''
        item['Class'] = ''

        trs = response.xpath('//table[@id="dgRegistration"]/tr')
        # print ('len(trs) = ' + str(len(trs)))
        if len(trs) > 1:
            for tr in trs:
                tds = tr.xpath('td')
                if ExtractAllText(tds[0]) == 'Owner':
                    continue

                item['Owner'] = ExtractAllText(tds[0])
                item['LastReg'] = ExtractAllText(tds[1].xpath('.//span[@id="dgRegistration__ctl2_lblLastReg"]'))
                item['RegExp'] = ExtractAllText(tds[1].xpath('.//span[@id="dgRegistration__ctl2_lblRegExp"]'))
                item['Organization'] = ExtractAllText(tds[2])
                item['LastNm'] = ExtractAllText(tds[3])
                item['FirstNm'] = ExtractAllText(tds[4])
                item['HouseNo'] = ExtractAllText(tds[5])
                item['StreetNm'] = ExtractAllText(tds[6])
                item['Apt'] = ExtractAllText(tds[7])
                item['City'] = ExtractAllText(tds[8])
                item['State'] = ExtractAllText(tds[9])
                item['Zip'] = ExtractAllText(tds[10])

                yield item
        yield Request(url=self.post_first, callback=self.parse, dont_filter=True)
