import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http import Request, FormRequest
from ProductsScraper.settings import *
import requests
import base64
import time

class LastcallSpider(scrapy.Spider):
    name = "lastcall"
    start_urls = ["http://www.lastcall.com/Clearance/Womens-Apparel/cat6400019_cat1230000_cat000000/c.cat"]

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url=url, headers={"Host": "www.lastcall.com",
                                            "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0",
                                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                                            "Accept-Language": "en-US,en;q=0.5",
                                            "Accept-Encoding": "gzip, deflate",
                                            "Connection": "keep-alive",
                                            "Upgrade-Insecure-Requests": "1"},
                                   callback=self.parse)

    def parse(self, response):
        page_num = 1

# POST /category.service?instart_disable_injection=true HTTP/1.1
# Host: www.lastcall.com
# User-Agent: Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:51.0) Gecko/20100101 Firefox/51.0
# Accept: */*
# Accept-Language: en-US,en;q=0.5
# Accept-Encoding: gzip, deflate
# Referer: http://www.lastcall.com/Clearance/Womens-Apparel/cat6400019_cat1230000_cat000000/c.cat
# X-Distil-Ajax: zbcfsrxazqfdzesryx
# Content-Type: application/x-www-form-urlencoded; charset=UTF-8
# X-Requested-With: XMLHttpRequest
# Content-Length: 791
# Cookie: D_SID=182.200.117.12:sAxWqydU7s8vaMs7roGmPv79U3gNX/CbXqVXW4yoAic; D_PID=3119DF0B-3C06-308A-88B4-6118E4B86D16; D_IID=0D47DBAF-D79C-3FC2-9F66-721B7B0E5E5B; D_UID=BFCFC728-CFFB-3D38-A8F7-FC7A51DD726E; D_HID=eJDixXPNa4ZF8QvQo1fnQW2Aa/mjMO/fZIqS6F7NWyM; D_ZID=4DF9A18E-F705-3E0E-844F-41D405CAA1AE; D_ZUID=E9887FC0-E03C-3E3E-A213-A734E2E95646; TLTUID=D50B076EF88210F853A1DCAF73544E40; AGA=""; mbox=PC#1487743950101-377233.24_6#1495684429|session#1487905273954-311829#1487910289|check#true#1487908489; utag_main=v_id:015a647322c1001e1c8e64a329750004d005600d00bd0$_sn:2$_ss:0$_st:1487910231888$_pn:6%3Bexp-session$ses_id:1487905275666%3Bexp-session$_prevpage:Clearance%3AWomen's%20Apparel%3Bexp-1487912032251; s_pers=%20productnum%3D7%7C1490500432305%3B; s_fid=662FBCAEE1A468F1-2611C21E703491F9; __qca=P0-581572361-1487743952677; bounceClientVisit1717=N4IgbiBcoJYC4FMC2BnA+jAdmgxgQwCc4oAzPAGxQQBoR8i0wKBXBUiq2uAezgrRR4wWAOYooIACQAGAHTTpIWoQIwmlNACM8mTAgLtKNOgAtuVbNxIl9hziBiaAHmkQpikMkdr0PX+zjczAAO3Nh4wcHkMAgAJnYIAL60KDDxkADMGbQkYB4AjAAsABwA7KX5AKwATBkAnLTC6UVlZQBsheXSdXUZpQ0geNxQ1bTkwRImcHDBAKQZAIKz1QBiyysA7luy5Hju+OTksoFI6wDC5AiEOjgI6wDq3EgImCgAtAuRhAjk6-hwHQU0nydVweDg+VqQOkYLg0IUf2O4KUg3EkHyjWCEEglVo6RA8VoBkgIC2Gx2ezgByOJxRODyUBapXanVKtBEOGJfVoSCg0jxaQkRWkpUK+XqWWKIuKdVK0lqKPIDPRJWZzLKbLoeCQwTwMBErygoAyxTFhTaRpASoKqvabXlYyEgpVrVKHS6PT6A12jNtbvtoxAJEEvo1VWqFWUaIxg2GkEDYGxMaEjOSIEKhWklVKGUt1tDao6ZUdTQLLI9vX6jrLbtVORDLvK4bqhSjjOUccDGxwNY6dRjifbgyTacK2ZKxTzyqZrQ1JedA+xlVH2cq0kKU5truKc6tTuajSXK9Ka4t0Ct09VFRq9XnB73BevtQGwbwj6qVWyqKgrdjP8SAFAA; _br_uid_2=uid%3D3508521739782%3Av%3D11.8%3Ats%3D1487743952879%3Ahc%3D10; __ibxl=1; rr_rcs=eF4FwbsNgDAMBcAmFbs8KYkdfzZgDecnUdAB83OXjvt7rsmkhMKmpi6U1RhkqFwap3ecHhLTKyFKLPBsA5nXhowmbiHau_-lSBKw; inside-usnm01=69076357-1095296c1c4d5f7264af5d6994cc9c6601e14f6805fb2f9ce3be15455fddd3de-0-0; DYN_USER_ID=2554574242; DYN_USER_CONFIRM=abcf5e23e1beeb29f3ae984411916a8a; WID=2554574242; sr_browser_id=beffa1cd-0e12-41d6-be70-b82141cc9151; CChipCookie=2030108682.4135.0000; TSde12a8=30d3a103fdffb54de5f04b639f07c9f7a02528836faba29058af3dcb8524428acd499c1c286023f2e9f24ffd60ac0ec5394dd59c219997379f802e8b219396cd1006d6876eedbc0a786bd524; clientipaddr=182.200.117.12; TLTSID=71456EEEF9FA10F9D144D8C6E76CC038; JSESSIONID=qQAef0Hf3fUTU6VmwwPEc3z+; W2A=2416771082.12075.0000; dtPC=508428162_287h6; dtSa=-; page_number=1; s_sess=%20s_ppvl%3Dhttp%25253A%252F%252Fwww.lastcall.com%252FClearance%252FWomens-Apparel%252Fcat6400019_cat1230000_cat000000%252Fc.cat%252C92%252C92%252C6245%252C1920%252C566%252C1920%252C1080%252C1%252CL%3B%20s_ppv%3Dhttp%25253A%252F%252Fwww.lastcall.com%252FYummie-Tummie-Strappy-Solid-Racerback-Sports-Bra-Women-s-Apparel%252Fprod42930088_cat6400019_cat1230000_cat000000%252Fp.prod%25253Ficid%25253D%252526searchType%25253DEndecaDrivenCat%252526rte%25253D%252525252Fcategory.jsp%252525253FitemId%252525253Dcat6400019%2525252526pageSize%252525253D30%2525252526No%252525253D0%2525252526refinements%252525253D%252526eItemId%25253Dprod42930088%252526cmCat%25253Dproduct%252C45%252C45%252C945%252C1920%252C945%252C1920%252C1080%252C1%252CL%3B; s_cc=true; dtLatC=307; s_sq=nmgincglobalprod%3D%2526c.%2526a.%2526activitymap.%2526page%253DClearance%25253AWomen%252527s%252520Apparel%2526link%253DNEXT%252520PAGE%2526region%253DepagingBottom%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c%2526pid%253DClearance%25253AWomen%252527s%252520Apparel%2526pidt%253D1%2526oid%253Dhttp%25253A%25252F%25252Fwww.lastcall.com%25252FClearance%25252FWomens-Apparel%25252Fcat6400019_cat1230000_cat000000%25252Fc.cat%252523%2526ot%253DA; bounceClientVisit1717v=N4IgNgDiBcIBYBcEQKQGYCCKBMAxHuA7sQHRgCGAzggMblhgk0D2AtgQMJgCm5ATuQB2NbgQDqbboMoBaDBAj9uYAnQQA2ACwAGXQEYAnAH01e7Gl26T5BJcuqmNkABoQfGCBABfIA; dtCookie=F15103D24901D89A76C760005E80D281|TEN8MQ
# Connection: keep-alive

# data=$b64$eyJHZW5lcmljU2VhcmNoUmVxIjp7InBhZ2VPZmZzZXQiOjEsInBhZ2VTaXplIjoiMzAiLCJyZWZpbmVtZW50cyI6IiIsInNlbGVjdGVkUmVjZW50U2l6ZSI6IiIsImFjdGl2ZUZhdm9yaXRlU2l6ZXNDb3VudCI6IjAiLCJhY3RpdmVJbnRlcmFjdGlvbiI6InRydWUiLCJtb2JpbGUiOmZhbHNlLCJzb3J0IjoiUENTX1NPUlQiLCJkZWZpbml0aW9uUGF0aCI6Ii9ubS9jb21tZXJjZS9wYWdlZGVmX3J3ZC90ZW1wbGF0ZS9FbmRlY2FEcml2ZW4iLCJ1c2VyQ29uc3RyYWluZWRSZXN1bHRzIjoidHJ1ZSIsInJ3ZCI6InRydWUiLCJhZHZhbmNlZEZpbHRlclJlcUl0ZW1zIjp7IlN0b3JlTG9jYXRpb25GaWx0ZXJSZXEiOlt7ImxvY2F0aW9uSW5wdXQiOiIiLCJyYWRpdXNJbnB1dCI6IjEwMCIsImFsbFN0b3Jlc0lucHV0IjoiZmFsc2UiLCJvbmxpbmVPbmx5IjoiIn1dfSwiY2F0ZWdvcnlJZCI6ImNhdDY0MDAwMTkiLCJzb3J0QnlGYXZvcml0ZXMiOmZhbHNlLCJpc0ZlYXR1cmVkU29ydCI6ZmFsc2UsInByZXZTb3J0IjoiIn19
# service=getCategoryGrid
# sid=getCategoryGrid
# bid=GenericSearchReq
# timestamp=1487908487117

# POST /category.service HTTP/1.1
# Host: www.lastcall.com
# User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0
# Accept: */*
# Accept-Language: en-US,en;q=0.5
# Accept-Encoding: gzip, deflate
# Referer: http://www.lastcall.com/Clearance/Womens-Apparel/cat6400019_cat1230000_cat000000/c.cat
# X-Distil-Ajax: zbcfsrxazqfdzesryx
# Content-Type: application/x-www-form-urlencoded; charset=UTF-8
# X-Requested-With: XMLHttpRequest
# Content-Length: 791
# Cookie: TSde12a8=1c2923867c7d46bc4ecd36446ec808cc408bfa5d2ac6b2d158c5af8d286023f28a599bf1ec2531808a599bf160ac0ec55c16dd90d72b81c02baa99cc2199973703728bdd219396cdc90daa7d8524428a9222a30b6eedbc0aa58cd089; D_SID=91.189.183.108:ovstGuBOaVV4FVPd1exSY+E3rYI7J1iL+T+XepmivVo; D_PID=3119DF0B-3C06-308A-88B4-6118E4B86D16; D_IID=F20244D3-29D3-3DB9-8535-09EE52EB20C6; D_UID=3D93CF5D-1A54-3DFE-B589-CD7181DC1790; D_HID=p3B2LBbHZD5cp1PFSSdKJcvtIiyH9ls0BO7GHG4vvdU; D_ZID=0F506EAB-6D8B-3B9F-8303-E287932A2712; D_ZUID=959E905C-CE1F-37BA-ADCF-D47758695865; TLTSID=CF38614A076110079AD49A2705667A06; TLTUID=CF38614A076110079AD49A2705667A06; JSESSIONID=EpaMLj+ieJdCuBMqFcs+qxoJ; AGA=""; W2A=2618097674.18475.0000; CChipCookie=2046885898.4135.0000; dtPC=-; dtSa=-; mbox=check#true#1489350296|session#1489350235287-467808#1489352096|PC#1489350235287-467808.26_18#1497126237; utag_main=v_id:015ac4311d74002da16c6adde5400004c005600900bd0$_sn:1$_ss:1$_pn:1%3Bexp-session$_st:1489352343112$ses_id:1489350237556%3Bexp-session$_prevpage:Clearance%3AWomen's%20Apparel%3Bexp-1489354143087; page_number=2; s_pers=%20productnum%3D1%7C1491942238698%3B; s_sess=%20s_ppvl%3Dhttp%25253A%252F%252Fwww.lastcall.com%252FClearance%252FWomens-Apparel%252Fcat6400019_cat1230000_cat000000%252Fc.cat%252C8%252C7%252C538%252C1855%252C481%252C1920%252C1080%252C1%252CL%3B%20s_ppv%3DClearance%25253AWomen%252527s%252520Apparel%252C17%252C17%252C481%252C1855%252C481%252C1920%252C1080%252C1%252CL%3B; s_fid=2A73DBEFA65FC43C-12053CC16C5E99BB; s_cc=true; bounceClientVisit1717v=N4IgNgDiBcIBYBcEQKQGYCCKBMAxHuA7sQHRgCGAzggMblhgk0D2AtgQMJgCm5ATuQB2NbgQDqbboMoBaDBAj9uYAnQQA2ACwAGXQEYAnAH01e7Gl26T5BJcuqmNkABoQfGCGKEyVWvUYsrCAAvkA; bounceClientVisit1717=N4IgbiBcoJYC4FMC2BnA+jAdmgxgQwCc4oAzPAGxQQBoR8i0wKBXBUiq2uAezgrRR4wWAOYooIACQAGAHTTpIWoQIwmlNACM8mTAgLtKNOgAtuVbNxIl9hziBiaAHmkQpikMkdr0PX+zjczAAO3Nh4wcHkMAgAJnYIAL60KDDxkAAstCRgHgCMGQAcAJwAzACs0gBMGdK0wukFJRXVtQBspRl5AOxVytxQebTkwRImcHDBAKSlAIJTVQBiC4sA7uuy5Hju+OTksoFIKwDC5AiEOjgIKwDq3EgImCgAtLORhAjkK-hwbbUKeWKuDwcDyVVKCgUwLgkMh3wOIKUIG2g3qwQgkCGIHS2KRBkgIHWq022zgu32hyROFygyKZUqNTqIBEOHxYNoSCgTNiaQkhVKJQyVWkxXK5UK0nK3UKVTyCiR5BpmLpLSqbW6PjwSGCeBgIieUFAGVqUvKhvAGKxivyKoZ6uGQl5yuaDPanR6fRAW1pLuq9uRluygh99L9GuR4kx-UGiVjQA; _br_uid_2=uid%3D4186812787552%3Av%3D11.8%3Ats%3D1489350240324%3Ahc%3D1; __ibxl=1; rr_rcs=eF4NxrERgCAMBdCGyl3iJXySwAauIUHuLOzU-fVVL6UntqyIiahkHQcV251kxvin1oV9evByvfc5VjhISm1QzmjCRpqJ5AOQwhGF; inside-usnm01=74566344-50ff6f04d68f0bdd24a6d37a17b091cededd7d155b6beaad383a511d9ce44e6c-0-0; s_sq=nmgincglobalprod%3D%2526c.%2526a.%2526activitymap.%2526page%253DClearance%25253AWomen%252527s%252520Apparel%2526link%253D1%252520PAGE%2526region%253DepagingTop%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c%2526pid%253DClearance%25253AWomen%252527s%252520Apparel%2526pidt%253D1%2526oid%253Dhttp%25253A%25252F%25252Fwww.lastcall.com%25252FClearance%25252FWomens-Apparel%25252Fcat6400019_cat1230000_cat000000%25252Fc.cat%252523%2526ot%253DA; om_prev_page=%7B%22sort_method_previous%22%3A%22BEST%20MATCH%22%7D; dtCookie=7D4A109F3827E42F02116B5F1FC8AC95|TEN8MQ
# Connection: keep-alive
    
        getpage_url = 'http://www.lastcall.com/category.service?instart_disable_injection=true'
        getpage_headers = {'Host': 'www.lastcall.com', 'X-Distil-Ajax': 'zbcfsrxazqfdzesryx', 'X-Requested-With': 'XMLHttpRequest',
                            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0',
                            'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5', 'Accept-Encoding': 'gzip, deflate',
                            'Referer': 'http://www.lastcall.com/Clearance/Womens-Apparel/cat6400019_cat1230000_cat000000/c.cat',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}
        # getpage_headers = {'X-Distil-Ajax': 'zbcfsrxazqfdzesryx', 'X-Requested-With': 'XMLHttpRequest'}
        getpage_formdata = {'data': '$b64$' + base64.b64encode('{"GenericSearchReq":{"pageOffset":%d,"pageSize":"30","refinements":"","selectedRecentSize":"","activeFavoriteSizesCount":"0","activeInteraction":"true","mobile":false,"sort":"PCS_SORT","definitionPath":"/nm/commerce/pagedef_rwd/template/EndecaDriven","userConstrainedResults":"true","rwd":"true","advancedFilterReqItems":{"StoreLocationFilterReq":[{"locationInput":"","radiusInput":"100","allStoresInput":"false","onlineOnly":""}]},"categoryId":"cat6400019","sortByFavorites":false,"isFeaturedSort":false,"prevSort":""}}' % page_num),
                            'service': 'getCategoryGrid',
                            'sid': 'getCategoryGrid',
                            'bid': 'GenericSearchReq',
                            'timestamp': str(time.time()).replace('.', '')}
        yield FormRequest(getpage_url, method='POST', headers=getpage_headers, formdata=getpage_formdata, dont_filter=True, callback=self.parse_page)
        # print requests.post(url=getpage_url, headers=getpage_headers, data=getpage_formdata).text
        # print response.url

    def parse_page(self, response):
        print (response.text)
