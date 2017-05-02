import scrapy
from ProductsScraper.items import Product
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re

class TruereligionSpider(scrapy.Spider):
    name = "truereligion"
    start_urls = [ # "http://www.truereligion.com/womens-sale",
                    'http://www.truereligion.com/womens-sale?sz=12&start=0&format=page-element']

    def __init__(self):
        self.start_num = 0
        self.nextpage_url = 'http://www.truereligion.com/womens-sale?sz=12&start=%d&format=page-element'

    def parse(self, response):
        products = response.xpath('//div[@class="product-tile"]')
        for prod in products:
            item = Product()

            item['Name'] = prod.xpath('div[@class="product-name"]/h2/a[@class="name-link"]/text()').extract_first().strip()
            item['original_url'] = response.urljoin(prod.xpath('div[@class="product-name"]/h2/a[@class="name-link"]/@href').extract_first())
            item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="product-pricing"]//span[@class="price-standard"]/text()').extract_first().strip())
            item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath('div[@class="product-pricing"]//span[@class="price-sales"]/text()').extract_first().strip())
            item['website_id'] = 15
            item['category_id'] = 2

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
            # break
        if len(products) > 0:
            self.start_num = self.start_num + len(products)
            yield Request(self.nextpage_url % self.start_num, callback=self.parse)

    def parse_detail(self, response):
        item = response.meta['item']

        item['original_image_url'] = [response.xpath('//ul[@id="carousel"]/li/a/img[@id="zoom_0"]/@src').extract_first()]
        item['image_urls'] = item['original_image_url']
        try:
            item['description'] = response.xpath('//div[@class="product-tabs"]/div[@id="tab1"]/p/text()').extract_first().strip()
        except:
            item['description'] = ''

        yield item
