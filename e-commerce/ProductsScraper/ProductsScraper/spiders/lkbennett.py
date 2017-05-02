import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re

class LkbennettSpider(scrapy.Spider):
    name = "lkbennett"
    start_urls = ["http://us.lkbennett.com/Collections/Sale/Clothing/c/sale-clothing"]

    def parse(self, response):
        sel = Selector(response)

        for prod in sel.xpath('//div[@class="productlist"]/div[@class="productrows"]//div[contains(@class, "prodgrid")]'):
            item = Product()

            item['Name'] = prod.xpath('span[@class="details"]/a/text()').extract_first().strip()
            item['original_url'] = response.urljoin(prod.xpath('span[@class="details"]/a/@href').extract_first()).strip()
            item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath('span[@class="cart"]/span[@class="wasPrice price"]/strike/text()').extract_first()).strip()
            item['sale_price'] = re.sub('[^\d\.]', '', ''.join(prod.xpath('span[@class="cart"]/text()').extract())).strip()
            item['website_id'] = 8
            item['category_id'] = 2

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
        #     break
        # return

        try:
            nextpage_url = response.urljoin(sel.xpath('//div[@class="pagination"]/div[@class="paginationlinks"]/ul/li[@class="next"]/a/@href').extract_first()).strip()
            if (nextpage_url is None) or (nextpage_url == ''):
                return
            yield Request(nextpage_url, callback=self.parse)
        except:
            pass

    def parse_detail(self, response):
        sel = Selector(response)
        item = response.meta['item']

        # item['description'] = ''.join(sel.xpath('//div[@class="prod-detail-accordian"]/div[@class="prod-detail-accordian-item open"]/h2/a[contains(text(), "Description")]/../../p//text()').extract()).strip()
        item['description'] = sel.xpath('//meta[@property="og:description"]/@content').extract_first()
        # item['original_image_url'] = [sel.xpath('//div[@class="amp-zoom-overflow"]/img[@class="amp-just-image amp-main-img amp-swap-source amp amp-zoom"]/@src').extract_first()]
        item['original_image_url'] = [sel.xpath('//meta[@property="og:image"]/@content').extract_first()]
        item['image_urls'] = item['original_image_url']

        yield item
