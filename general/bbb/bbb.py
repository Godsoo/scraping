from scrapex import *
import re

s = Scraper(use_cache=True, retries=3, timeout=30)

logger = s.logger

site_name = 'bbb'
site_url = 'http://www.bbb.org'

def parse_detail(doc):
    # 6269 Leesburg Pike Ste 309 Seven Corners, VA 22044-2103
    # 315 N Broadway Ave Tyler, TX 75702-5712
    # Albuquerque, NM 87101
    # 1491 River Park Dr. Ste. 101 Sacramento, CA 95815
    address = doc.q('//div[@id="company-info-area"]//address//text()').join(' ')
    # zipcode = re.search('\,\s[\w]{2}\s([0-9\-]+)?').group(1)
    # state = re.search('\,\s([\w]{2})\s[0-9\-]*').group(1)

    return ['phone_num', doc.x('//div[@id="company-info-area"]//h3[@class="address__heading"]/a[@class="address__phone-number-link"]/text()').strip(), 
            'name', doc.x('//div[@id="company-info-area"]//h1[@class="address__sub-heading"]/text()').strip(), 
            'experience', doc.x('//div[@id="company-info-area"]//h5[@class="address__sub-heading"]/text()').strip(), 
            'address', address,
            'email', re.sub('mailto\:', '', doc.x('//div[@id="company-info-area"]//div[@class="business-buttons"]/a[contains(@href, "mailto:")]/@href')),
            'website', doc.x('//div[@id="company-info-area"]//div[@class="business-buttons"]/a[contains(text(), "WEBSITE")]/@href'),
            'fax', doc.q('//div[@id="company-info-area"]//div[@id="SeeMoreContactOptions"]//h6[contains(text(), "Fax Numbers")]/../ul/li/text()').join('|'),
            'BBB_File_Opened', doc.q('//div[@id="company-info-area"]//div[contains(text(), "BBB File Opened:")]//text()').join('').replace('BBB File Opened:', '').strip(),
            'Business_Started', doc.q('//div[@id="company-info-area"]//div[contains(text(), "Business Started:")]//text()').join('').replace('Business Started:', '').strip(),
            'Business_Incorporated', doc.q('//div[@id="company-info-area"]//div[contains(text(), "Business Incorporated:")]//text()').join('').replace('Business Incorporated:', '').strip(),
            'Type_of_Entity', doc.q('//div[@id="company-info-area"]//h6[contains(text(), "Type of Entity")]/../text()').join('').replace('Type of Entity', '').strip(),
            'Business_Management', doc.q('//div[@id="company-info-area"]//h6[contains(text(), "Business Management")]/../ul/li/text()').join('|').strip(),
            'Contact_Information', doc.q('//div[@id="company-info-area"]//h6[contains(text(), "Contact Information")]/../ul/li/text()').join('|').strip(),
            'Business_Category', doc.q('//div[@id="company-info-area"]//h6[contains(text(), "Business Category")]/..//ul/li/text()').join('|').strip()]

# keywords: Latino, Hispanic
# zipcode: 10001

def search(keyword, zipcode):
    if (not keyword) or (not zipcode):
        return
    # search_url = 'http://www.bbb.org/search/?splashPage=true&type=name&input=%s&location=%s&tobid=&filter=business&source=bbbse&default-source=bbbad&radius=&accredited=accredited&country=USA,CAN&language=en&codeType=YPPA' % (keyword, zipcode)
    search_url = 'http://www.bbb.org/search/?splashPage=true&type=name&input=%s&location=%s&tobid=&filter=combined&source=bbbse&default-source=bbbad&radius=&accredited=accredited&country=USA&language=en&codeType=YPPA' % (keyword, zipcode)
    while 1:
        doc = s.load(search_url)

        companies = doc.q('//table[@class="search-results-table table table-condensed"]/tbody/tr/td/h4/a')
        logger.info(search_url + ' -> ' + str(len(companies)))
        if len(companies) == 0:
            break
        search_url = doc.x('//nav[@class="search-results-pagination"]/ul[@class="pager"]/li[@class="next"]/a/@href')
        for row in companies:
            company_info = parse_detail(s.load(row.x('@href')))
            # logger.info(str(company_info))
            if (company_info[3]) is None or (company_info[3] == ''):
                continue
            s.save(company_info, 'result.csv')
        if not search_url:
            break

if __name__ == '__main__':
    search('Latino', '10001')
    search('Hispanic', '10001')
