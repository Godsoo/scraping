import scrapy
from ProductsScraper.items import Product
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re

class LadyfootlockerSpider(scrapy.Spider):
    name = "ladyfootlocker"
    start_urls = ["http://www.ladyfootlocker.com/Sale/Clothing/_-_/N-1z141ydZrk?cm_REF=Clothing&Nr=AND%28P_RecordType%3AProduct%29"]

    def parse(self, response):
        products = response.xpath("//div[@class='mainsite_record_listing']/div[@id='endeca_search_results']/ul/li[not(@class)]")
        # print len(products)
        if len(products) == 0:
            return
        for prod in products:
            item = Product()

            item['Name'] = ''.join(prod.xpath('a[not(@onmousedown)]/text()').extract()).strip()
            item['original_url'] = prod.xpath('a[not(@onmousedown)]/@href').extract_first()
            item['reg_price'] = re.sub('[^\d\.\,]', '', prod.xpath("p[@class='product_price']/strike/b/text()").extract_first()).strip()
            item['sale_price'] = re.sub('[^\d\.\,]', '', prod.xpath("p[@class='product_price']/em/b/text()").extract_first()).strip()
            item['website_id'] = 21
            item['category_id'] = 2

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
            # break

        next_page = response.xpath("//div[@class='endeca_pagination']/a[@class='next']/@href").extract_first()
        if next_page:
            yield Request(response.urljoin(next_page), callback=self.parse, dont_filter=True)

    def parse_detail(self, response):
        item = response.meta['item']

        item['description'] = response.xpath("//meta[@name='description']/@content").extract_first()
        item['original_image_url'] = ["http:" + response.xpath('//meta[@property="og:image"]/@content').extract_first()]
        item['image_urls'] = item['original_image_url']

        yield item
