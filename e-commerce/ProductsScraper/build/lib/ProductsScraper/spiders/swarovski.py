import scrapy
from ProductsScraper.items import Product
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re
import requests

class SwarovskiSpider(scrapy.Spider):
    name = "swarovski"
    start_urls = ["http://www.swarovski.com/Web_US/en/1001/category/OUTLET/Necklaces.html"]

    def parse(self, response):
        # e.g. http://www.swarovski.com/Web_US/en/json/json-result?SearchParameter=%26%40QueryTerm%3D*%26CategoryUUIDLevelX%3DkTUKaSUCyn4AAAEnV9lToUKM%26CategoryUUIDLevelX%252FkTUKaSUCyn4AAAEnV9lToUKM%3DInYKaVgfvWsAAAFaO6s2M2Wp%26CategoryUUIDLevelX%252FkTUKaSUCyn4AAAEnV9lToUKM%252FInYKaVgfvWsAAAFaO6s2M2Wp%3DTxcKaVgfw6MAAAFaOqs2M2Wp%26%40Sort.FFSort%3D0%26%40Page%3D2&PageSize=36&View=M
        page_num = 1
        while 1:
            ajax_url = 'http://www.swarovski.com/Web_US/en/json/json-result?SearchParameter=%26%40QueryTerm%3D*%26CategoryUUIDLevelX%3DkTUKaSUCyn4AAAEnV9lToUKM%26CategoryUUIDLevelX%252FkTUKaSUCyn4AAAEnV9lToUKM%3DInYKaVgfvWsAAAFaO6s2M2Wp%26CategoryUUIDLevelX%252FkTUKaSUCyn4AAAEnV9lToUKM%252FInYKaVgfvWsAAAFaO6s2M2Wp%3DTxcKaVgfw6MAAAFaOqs2M2Wp%26%40Sort.FFSort%3D0%26%40Page%3D' + str(page_num) + '&PageSize=36&View=M'
            products = requests.get(ajax_url, headers={'X-Requested-With': 'XMLHttpRequest'}).json()['SearchResult']['Products']
            for prod in products:
                item = Product()

                item['Name'] = prod['Name']
                item['original_url'] = prod['DetailPage']
                item['reg_price'] = re.sub('[^\d\.]', '', prod['OldPrice'])
                item['sale_price'] = re.sub('[^\d\.]', '', prod['Price'])
                item['website_id'] = 18
                item['category_id'] = 4
                item['discount'] = re.sub('[^\d]', '', prod['PricePercent'])

                yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
                # break
            if len(products) < 36:
                break
            page_num = page_num + 1
            # break

    def parse_detail(self, response):
        item = response.meta['item']

        item['description'] = response.xpath('//meta[@name="description"]/@content').extract_first()
        # image_url = response.xpath('//div[@class="prod-altviews"]/ul/li/a[@href="-"]/img/@data-elevatezoomLargeimg').extract_first()
        image_url = response.urljoin(response.xpath('//div[@class="prod-altviews"]/ul/li/a[@href="-"]/img/@src').extract_first())
        item['original_image_url'] = [image_url]
        item['image_urls'] = item['original_image_url']

        yield item
