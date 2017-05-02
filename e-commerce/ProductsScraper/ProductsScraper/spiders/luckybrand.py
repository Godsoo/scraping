import scrapy
from ProductsScraper.items import Product
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re

class LuckybrandSpider(scrapy.Spider):
    name = "luckybrand"
    start_urls = ["http://www.luckybrand.com/sale/womens/jeans"]

    def parse(self, response):
        products = response.xpath('//ul/li/div[@class="product-tile"]')
        # print len(products)
        for prod in products:
            item = Product()
            item['Name'] = prod.xpath('h6[@class="product-name"]/a[@class="name-link"]/text()').extract_first().strip()
            item['original_url'] = prod.xpath('h6[@class="product-name"]/a[@class="name-link"]/@href').extract_first().strip()
            try:
                item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="product-pricing"]/span[@title="Regular Price"]/text()').extract_first().strip())
            except:
                item['reg_price'] = '0.0'
            try:
                item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="product-pricing"]/span[@title="Sale Price"]/text()').extract_first().strip())
            except:
                item['sale_price'] = '0.0'
            item['website_id'] = 16
            item['category_id'] = 2
            # item['discount'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="product-promo promotion"]/span[@class="promotional-message PRODUCT"]/text()').extract_first().strip())

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
            # break

    def parse_detail(self, response):
        item = response.meta['item']

        item['original_image_url'] = [response.xpath('//picture/img[@itemprop="image"]/@src').extract_first()]
        item['image_urls'] = item['original_image_url']
        item['description'] = re.sub('^Details', '', ' '.join([frag.strip() for frag in response.xpath('//div[@class="product-info-tiles"]/div[@class="product--info"]/h5[contains(text(), "Details")]/..//text()').extract()]).strip())

        yield item
