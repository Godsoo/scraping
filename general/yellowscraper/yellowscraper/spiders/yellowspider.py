# /media/simon/mine/mine/scrape/job/JP/program/yellowscraper/yellowscraper/spiders

from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from yellowscraper.items import YellowscraperItem
from yellowscraper.items import ArticleItem
from bs4 import BeautifulSoup
from lxml import html
import csv
import re
import requests


class yellowspider(Spider):
    name = "yellowspider"
    start_urls = [
            "http://www.yellow-pages.ph/sitemap.xml",
            # "https://www.google.com.ph/search?q=site%3Ayellow-pages.ph&rlz=1C1GNAM_enPH691PH691&oq=site%3Ayellow-pages.ph&aqs=chrome..69i57j69i58j69i60.4097j0j1&sourceid=chrome&ie=UTF-8",   -- google "site:yellow-pages.ph"
            # "http://cn.bing.com/search?q=site%3Ayellow-pages.ph&qs=n&form=QBRE&pq=site%3Ayellow-pages.ph&sc=0-20&sp=-1&sk=&cvid=1D0415DECE8E432EA578EC6EC76CA91F",
            # "http://global.bing.com/search?q=site%3Ayellow-pages.ph&qs=n&form=QBRE&pq=site%3Ayellow-pages.ph&sc=0-20&sp=-1&sk=&cvid=CE2C5548A71448F68B49A347A48014DC",
            # "https://www.google.com/webhp?sourceid=chrome-instant&ion=1&espv=2&ie=UTF-8#q=site%3Ayellow-pages.ph",
            # "http://www.yellow-pages.ph/business/imatech-corporation",
            # "http://www.yellow-pages.ph/business/barangay-poblacion",
            # "http://www.yellow-pages.ph/business/basic-taxi",
            # "http://www.yellow-pages.ph/business/titan-shop",
            # "http://www.yellow-pages.ph/business/basic-taxi",
            # "http://www.yellow-pages.ph/business/imatech-corporation",
            # "http://www.yellow-pages.ph/business/istorya-creations",
            # "http://www.yellow-pages.ph/business/titan-shop",
        ]

    def __init__(self):

        self.page_num = 0

        # self.base_url = 'https://www.google.com.ph'


    def parse(self, response) :

        res = requests.get(response.url)

        # Response
        # print( res.status_code )# Response Code  
        # print( res.headers )# Response Headers  
        # print( res.content )# Response Body Content

        # Request
        # print( res.request.headers ) # Headers you sent with the request  

        # Parse the body into a tree
        sitemap = html.fromstring(res.content)

        # Perform xpaths on the tree
        # print parsed_body.xpath('//title/text()') # Get page title  
        # print parsed_body.xpath('//a/@href') # Get href attribute of all links  


        for loc in sitemap.xpath('//loc/text()') :

            # if ( self.page_num > 0 ) :

            #     return

            res_biz = requests.get(loc.strip())

            res_biz_sitemap = html.fromstring(res_biz.content)

            temp_num = 0

            for biz_url in res_biz_sitemap.xpath('//loc/text()') :

                # if ( temp_num > 3 ) :
                #     break

                if ( biz_url.find('/business/') != -1 ) :

                    yield Request(url=biz_url.strip(), callback=self.parse_detail)

                    # temp_num = temp_num + 1

                # item = YellowscraperItem()

                # item['link'] = loc

                # yield item

            # self.page_num = self.page_num + 1

        # ####################################    google "site:yellow-pages.ph"  ##########################

        # for business in response.xpath('//div/h3/a[contains(@href, "www.yellow-pages.ph/business/")]/@href'):
        # # for business in response.xpath('//div[@id="b_content"]/ol/li/h2/a/@href') :   ------------ bing

        #     # item = YellowscraperItem()

        #     # item['link'] = self.base_url + business.extract()
        #     # # item['link'] = business.extract()

        #     # yield item

        #     yield Request(url=self.base_url + business.extract(), callback=self.parse_detail)

        # self.page_num = self.page_num + 1

        # if ( len(response.xpath('//div[@id="foot"]/table/tr/td/a/span[contains(text(),"Next")]/../@href').extract()) > 0 ) :
        # # if ( len(response.xpath('//a[@class="sb_pagN"]/@href').extract()) > 0 ) :     ------------ bing
        # # if ( self.page_num < 10 ) :

        #     # yield Request(url='http://cn.bing.com/' + response.xpath('//a[@class="sb_pagN"]/@href').extract()[0], callback=self.parse)    ------------- bing
        #     yield Request(url=self.base_url + response.xpath('//div[@id="foot"]/table/tr/td/a/span[contains(text(),"Next")]/../@href').extract()[0], callback=self.parse)


    def parse_detail(self, response) :

        item = YellowscraperItem()

        item['link'] = response.url

        div_middle = response.xpath('//div[@class="result-middle"]')

        if ( div_middle ) :

            item['name'] = div_middle.xpath('//h1[@class="result-name uppercase"]/text()').extract()

            if ( len(item['name']) == 1 ) :

                item['name'] = item['name'][0]

            item['alt_name'] = div_middle.xpath('//h2[@class="result-co uppercase"]/text()').extract()

            if ( len(item['alt_name']) == 1 ) :

                item['alt_name'] = item['alt_name'][0]

            div_address = div_middle.xpath('div[@class="result-address"]')

            if ( div_address ) :

                item['address'] = div_address.xpath('h3/text()').extract()

                if ( len(item['address']) == 1 ) :

                    item['address'] = item['address'][0]

            div_phone_main = div_middle.xpath('div[@class="result-phone"]')

            if ( div_phone_main ) :

                item['phone_main'] = div_phone_main.xpath('h4/text()').extract()

                if ( len(item['phone_main']) == 1 ) :

                    item['phone_main'] = item['phone_main'][0]


        div_moreinfo = response.xpath('//div[@id="tab-moreinfo"]')

        if ( div_moreinfo ) :

            div_about_left = div_moreinfo.xpath('//div[@class="header-left"]/span[contains(text(), "About")]/..')

            if ( div_about_left ) :

                div_about_right = div_about_left.xpath('following-sibling::div[@class="content-right"]')

                if ( div_about_right ) :

                    item['about'] = div_about_right.xpath('p/text()').extract()

                    if ( len(item['about']) == 1 ) :

                        item['about'] = item['about'][0]

            div_fax = div_moreinfo.xpath('//div[@class="content-right"]/small[contains(text(), "Fax")]')

            if ( div_fax ) :

                item['fax'] = div_fax.xpath('normalize-space(following-sibling::text())').extract()

                if ( len(item['fax']) == 1 ) :

                    item['fax'] = item['fax'][0]

            div_email = div_moreinfo.xpath('//div[@class="content-right"]/small[contains(text(), "Email")]')

            if ( div_email ) :

                item['email'] = div_email.xpath('normalize-space(following-sibling::a/text())').extract()

                if ( len(item['email']) == 1 ) :
                    
                    item['email'] = item['email'][0]

            div_website = div_moreinfo.xpath('//div[@class="content-right"]/small[contains(text(), "Website")]')

            if ( div_website ) :

                item['website'] = div_website.xpath('normalize-space(following-sibling::a/text())').extract()

                if ( len(item['website']) == 1 ) :
                    
                    item['website'] = item['website'][0]

            div_phone_addi = div_moreinfo.xpath('//div[@class="content-right"]/small[contains(text(), "Phone")]')

            if ( div_phone_addi ) :

                item['phone_addi'] = div_phone_addi.xpath('normalize-space(following-sibling::text())').extract()

                if ( len(item['phone_addi']) == 1 ) :
                    
                    item['phone_addi'] = item['phone_addi'][0]


            div_phone_mobi = div_moreinfo.xpath('//div[@class="content-right"]/small[contains(text(), "Mobile")]')

            if ( div_phone_mobi ) :

                item['phone_mobi'] = div_phone_mobi.xpath('normalize-space(following-sibling::text())').extract()

                if ( len(item['phone_mobi']) == 1 ) :
                    
                    item['phone_mobi'] = item['phone_mobi'][0]


            div_prod_serv_left = div_moreinfo.xpath('//div[@class="header-left"]/span[contains(text(), "Products & Services")]/..')

            if ( div_prod_serv_left ) :

                div_prod_serv_right = div_prod_serv_left.xpath('following-sibling::div[@class="content-right"]')

                if ( div_prod_serv_right ) :

                    item['prod_serv'] = div_prod_serv_right.xpath('div/div/ul/li/text()').extract()


            div_prim_catg = div_moreinfo.xpath('//div[@class="content-right"]/span/strong[contains(text(), "Primary Categories:")]')

            if ( div_prim_catg ) :

                item['prim_catg'] = div_prim_catg.xpath('../following-sibling::ul[1]/li/text()').extract()


            div_othe_catg = div_moreinfo.xpath('//div[@class="content-right"]/span/strong[contains(text(), "Other Categories:")]')

            if ( div_othe_catg ) :

                item['othe_catg'] = div_othe_catg.xpath('../following-sibling::ul[1]/li/text()').extract()


            div_tags_left = div_moreinfo.xpath('//div[@class="header-left"]/span[contains(text(), "Tags")]/..')

            if ( div_tags_left ) :

                div_tags_right = div_tags_left.xpath('following-sibling::div[@class="content-right"]')

                if ( div_tags_right ) :

                    item['tags'] = div_tags_right.xpath('text()').extract()

                    if ( len(item['tags']) == 1 ) :
                        
                        item['tags'] = item['tags'][0]

            div_spec_feat_left = div_moreinfo.xpath('//div[@class="header-left"]/span[contains(text(), "Special Features")]/..')

            if ( div_spec_feat_left ) :

                div_spec_feat_right = div_spec_feat_left.xpath('following-sibling::div[@class="content-right"]')

                if ( div_spec_feat_right ) :

                    item['spec_feat'] = div_spec_feat_right.xpath('div/ul/li/text()').extract()


        # print( response.xpath('//input[@id="business_id"]') )

        # #########################################      articles tab       ############################################

        # business_id = response.xpath('//input[@id="business_id"]/@value').extract()

        # if ( len(business_id) == 1 ) :

        #     business_id = business_id[0]

        #     articles_ajax_url = 'http://www.yellow-pages.ph/business_article/business_articles/%s' % business_id

        #     articles_response = requests.get(
        #                                             url= articles_ajax_url,
        #                                         headers= {       'Host': "www.yellow-pages.ph",
        #                                                   'User-Agent': "Mozilla/5.0 (Windows NT 6.3; Win64; x64; rv:46.0) Gecko/20100101 Firefox/46.0",
        #                                                       'Accept': "*/*",
        #                                              'Accept-Language': "en-US,en;q=0.5",
        #                                              'Accept-Encoding': "gzip, deflate",
        #                                             'X-Requested-With': "XMLHttpRequest",
        #                                                      'Referer': response.url,
        #                                                   'Connection': "keep-alive" }
        #                                     )

        #     # print( articles_response.text )

        #     [first, raw_html] = articles_response.text.split('$(".tab-articles-content-1").html')

        #     raw_html = raw_html.replace('\\n', '').replace('\\', '').strip('(\"').strip('\");')

        #     soup = BeautifulSoup( raw_html )


        #     div_article_container = soup.find('div', attrs={'id' : "arank"})


            

        #     # item['articles'] = response.xpath('//a[@id="t-articles"]').extract()

        #     item['articles'] = []

        #     if ( div_article_container ) :

        #         div_article_items = div_article_container.find_all('div', attrs={'class':'article-item'})

        #         for article in div_article_items :

        #             div_article_content = article.find('div', attrs={'class':'article-content'})

        #             item_article = ArticleItem()

        #             if ( div_article_content ) :


        #                 item_article['title'] = div_article_content.find('h4', attrs={'class':'article-title'}).a.get_text()

        #                 if ( len(item_article['title']) == 1 ) :

        #                     item_article['title'] = item_article['title'][0]


        #                 item_article['detail'] = div_article_content.find('h4', attrs={'class':'article-title'}).a['href']

        #                 if ( len(item_article['detail']) == 1 ) :

        #                     item_article['detail'] = item_article['detail'][0]


        #                 item_article['desc'] = div_article_content.find('div', attrs={'class':'article-review'}).findNext('p').get_text().split('read full article on')[0].strip()

        #                 if ( len(item_article['desc']) == 1 ) :

        #                     item_article['desc'] = item_article['desc'][0]


        #                 item_article['author'] = div_article_content.find('div', attrs={'class':'article-author-uploaded'}).get_text().strip()

        #                 if ( len(item_article['author']) == 1 ) :

        #                     item_article['author'] = item_article['author'][0]

        #             item['articles'].append( item_article )


        yield item

