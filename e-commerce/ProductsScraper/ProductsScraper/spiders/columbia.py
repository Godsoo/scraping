import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re
import requests

class ColumbiaSpider(scrapy.Spider):
    name = "columbia"
    start_urls = [ # "http://www.columbia.com/sale-discount-womens-jackets-vests/",
                    'http://www.columbia.com/sale-discount-womens-jackets-vests/?sz=300&start=0&format=page-element']

    def parse(self, response):
        products = response.xpath('//ul[@id="search-result-items"]/li/div[@class="product-tile"]')
        for prod in products:
            item = Product()
            item['Name'] = prod.xpath('div[@class="product-caption"]/div[@class="product-name"]/h2/a/text()').extract_first().strip()
            item['original_url'] = prod.xpath('div[@class="product-caption"]/div[@class="product-name"]/h2/a/@href').extract_first().strip()
            try:
                item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="product-caption"]/div[@class="product-pricing"]//span[@title="Regular Price"]/text()').extract_first().strip())
            except:
                item['reg_price'] = '0.0'
            try:
                item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="product-caption"]/div[@class="product-pricing"]//span[@title="Sale Price"]/text()').extract_first().strip())
            except:
                item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="product-caption"]/div[@class="product-pricing"]/span[@class="product-sales-price"]/text()').extract_first().strip().split('-')[0])
            item['website_id'] = 13
            item['category_id'] = 2
            item['original_image_url'] = [prod.xpath('div[@class="product-image"]/a/img[@class="product-image"]/@src').extract_first()]
            item['image_urls'] = item['original_image_url']

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)

    def parse_detail(self, response):
        item = response.meta['item']
        try:
            item['description'] = response.xpath('//div[@class="product_details_wrapper"]/div[@class="product-summary"]/text()').extract_first().strip()
        except:
            item['description'] = ''
        yield item
