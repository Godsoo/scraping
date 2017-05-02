# /media/simon/mine/mine/scrape/nicolas/program/hotelscraper/hotelscraper/spiders
import csv
from selenium import webdriver
from scrapy.spiders import Spider
from scrapy.selector import Selector
from scrapy.http import Request
from hotelscraper.items import HotelscraperItem
from selenium import webdriver

class momondospider(Spider):
    name = "momondospider"
    start_urls = [
        "http://www.momondo.com/hotels/s/nicaragua?rooms=2&overview=false&context=89244-1&type=0,7", # nicaragua
        # "http://www.momondo.com/hotels/s/costa-rica?rooms=2&overview=false&context=89244-2&type=0,7", # costa rica
        # "http://www.momondo.com/hotels/s/bali?checkin=&checkout=&rooms=2&overview=false&context=09477-1&type=0,7", # bali indonesia
        # "http://www.momondo.com/hotels/s/gili-islands?rooms=2&overview=false&context=09477-2&type=0,7", # gili islands indonesia
        ]

    def __init__(self):

        # self.profile = webdriver.FirefoxProfile("/home/simon/.mozilla/firefox/yt6zm4r7.default")
        self.profile = webdriver.FirefoxProfile("C:\\Users\\VALEN\\AppData\\Roaming\\Mozilla\\Firefox\\Profiles\\xr3uv8gr.default")
        self.driver  = webdriver.Firefox(self.profile)


    def parse(self, response):

        self.driver.get( response.url )

        page_num = 0

        while ( 1 ) :

            hxs = Selector(text=self.driver.page_source)

            while ( (len(hxs.xpath('//div[@class="hotels-results-toolbar hotels-results-toolbar--bottom ng-scope"]/ul/li[contains(@class, "control-pagination-item--page-current")]/div/span/span[@class="label ng-binding"]/text()').extract()) == 0) or (len(hxs.xpath('//div[contains(text(), "Loading more hotels")]').extract()) > 0) ) :

                hxs = Selector(text=self.driver.page_source)

            for hotel in hxs.xpath('//div[@class="hotels-result ng-isolate-scope"]') :

                item = HotelscraperItem()


                item['name']  = hotel.xpath('div/div/div[@class="hotels-result-name"]/a/text()').extract()

                item['price'] = hotel.xpath('div/div/div/div/span/div[@class="hotels-result-offer-price hotels-result-offer-price--lowest"]/span[1]/text()').extract()

                self.driver.find_element_by_xpath( '//div[@class="hotels-result-name"]/a[contains(text(), "' + item['name'][0] + '")]').click()

                while ( 1 ) :

                    expanded = Selector(text=self.driver.page_source)

                    item['street']  = expanded.xpath('//div[@class="hotels-expanded-content-address"]/ul/li[@class="hotels-expanded-content-address-item hotels-expanded-adress--street ng-binding"]/text()').extract()

                    item['area']    = expanded.xpath('//div[@class="hotels-expanded-content-address"]/ul/li[@class="hotels-expanded-content-address-item hotels-expanded-adress--area ng-binding"]/text()').extract()

                    item['country'] = expanded.xpath('//div[@class="hotels-expanded-content-address"]/ul/li[@class="hotels-expanded-content-address-item hotels-expanded-adress--country ng-binding"]/text()').extract()

                    if ( (len(item['street']) != 0) or (len(item['area']) != 0) or (len(item['country']) != 0) ) :

                        break

                if ( len(item['price']) > 0 ) :
                    item['price'][0] = item['price'][0] + "USD"
                else:
                    item['price'] = ["0"]

                yield item

            if ( len(hxs.xpath( '//div[@class="control-button"]/span/i[@class="icon icon-size--24 icon--chevron-east"]' ).extract()) == 0 ) :

                break

            else:
                self.driver.find_element_by_xpath( '//div[@class="control-button"]/span/i[@class="icon icon-size--24 icon--chevron-east"]' ).click()

                self.driver.implicitly_wait(40)

                page_num = page_num + 1


