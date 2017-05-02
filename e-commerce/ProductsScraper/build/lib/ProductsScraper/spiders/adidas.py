import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re

class AdidasSpider(scrapy.Spider):
    name = "adidas"
    start_urls = ['http://www.adidas.com/us/women-apparel-sale']

    def __init__(self):
        self.page_num = 0
        self.nextpage_url = 'http://www.adidas.com/us/women-apparel-sale?start=%d'

    def parse(self, response):
    	products = response.xpath('//div[@id="product-grid"]//div[@class="product-tile"]//div[contains(@class, "innercard  col")]')
    	if len(products) == 0:
    		return
    	self.page_num = self.page_num + len(products)
        for prod in products:
            item = Product()

            item['Name'] = prod.xpath('div/div[@class="product-info-inner-content clearfix with-badges"]/a/@data-productname').extract_first().strip()
            item['original_url'] = prod.xpath('div/div[@class="product-info-inner-content clearfix with-badges"]/a/@href').extract_first().strip()
            item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath('.//div[@class="price"]/span[@class="strike"]/span[@class="baseprice"]/text()').extract_first()).strip()
            item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath('.//div[@class="price"]/span[@class="salesprice discount-price"]/text()').extract_first()).strip()
            item['website_id'] = 11
            item['category_id'] = 2
            item['discount'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="badge sale"]/span[@class="badge-text"]/text()').extract_first()).strip()

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
            # break
        # return
        yield Request(self.nextpage_url % self.page_num, callback=self.parse)

    def parse_detail(self, response):
        item = response.meta['item']

        item['description'] = response.xpath('//segment[contains(@class, "product-segment ProductDescription")]//div[@itemprop="description"]/text()').extract_first().strip()
        image_url = response.xpath('//div[@id="main-image"]/a/img[@class="productimagezoomable"]/@src').extract_first()
        if 'http:' not in image_url:
            image_url = 'http:' + image_url
        item['original_image_url'] = [image_url]
        item['image_urls'] = item['original_image_url']

        yield item
