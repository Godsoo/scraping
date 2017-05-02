import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re
# import html
import HTMLParser

class AeropostaleSpider(scrapy.Spider):
    name = "aeropostale"
    start_urls = ["http://www.aeropostale.com/girls-clothing/features/clearance/family.jsp?categoryId=119431756&cp=3534618.3534619.3534626.3595054&content=topNav"]

    def __init__(self):
        self.page_num = 0
        self.nextpage_url = 'http://www.aeropostale.com/girls-clothing/features/clearance/family.jsp?page=%d&categoryId=119431756&cp=3534618.3534619.3534626.3595054'
        self.setcurrency_url = 'http://www.aeropostale.com/include/intlSetCountryCurrency.jsp?selCountry=United+States&selCurrency=US+Dollar+(USD)'
        self.usd_set = 0

    def parse(self, response):
        if self.usd_set == 0:
            self.usd_set = 1
            yield Request(self.setcurrency_url, callback=self.parse)
            return
        elif self.page_num == 0:
            self.page_num = 1
            yield Request(self.nextpage_url % self.page_num, callback=self.parse)
            return

        products = response.xpath('//div[@id="products"]//div[@class="item first"]/div[@class="details"]/div[@class="details-content"]')
        # print len(products)
        for prod in products:
            item = Product()

            item['Name'] = prod.xpath('h4/a/text()').extract_first().strip()
            item['original_url'] = response.urljoin(prod.xpath('h4/a/@href').extract_first())
            item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath('ul[@class="price"]/li[not(@class)]/text()').extract_first()).strip()
            item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath('ul[@class="price"]/li[@class="now"]/text()').extract_first()).strip()
            item['website_id'] = 14
            item['category_id'] = 2

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
            # break
        # return

        if len(products) > 0:
            self.page_num = self.page_num + 1
            yield Request(self.nextpage_url % self.page_num, callback=self.parse)

    def parse_detail(self, response):
        item = response.meta['item']

        item['description'] = re.sub(r'\<[\w]*\>', ' ', HTMLParser.HTMLParser().unescape(response.xpath('//meta[@property="og:description"]/@content').extract_first()))
        item['original_image_url'] = [response.xpath('//meta[@property="og:image"]/@content').extract_first()]
        item['image_urls'] = item['original_image_url']

        yield item
