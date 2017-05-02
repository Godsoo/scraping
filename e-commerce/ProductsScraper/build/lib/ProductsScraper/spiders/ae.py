import scrapy
from ProductsScraper.items import Product
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re

class AeSpider(scrapy.Spider):
    name = "ae"
    start_urls = ["https://www.ae.com/women-clearance-tops/web/s-cat/6470588?cm=sUS-cUSD&navdetail=mega:clearance:c1:p2"]

    def parse(self, response):
        products = response.xpath("//div[@class='product-list']/div/div[@class='product-details-container']")
        for prod in products:
            item = Product()

            item['Name'] = prod.xpath(".//h4/span[@itemprop='name']/text()").extract_first().strip()
            item['original_url'] = response.urljoin(prod.xpath("a/@href").extract_first())
            item['reg_price'] = re.sub('[^\d\.]', '', prod.xpath(".//span[@itemprop='offers']/s/span[@itemprop='price']/text()").extract_first().strip())
            item['sale_price'] = re.sub('[^\d\.]', '', prod.xpath(".//span[@itemprop='offers']/span[@itemprop='price']/text()").extract_first().strip())
            item['website_id'] = 23
            item['category_id'] = 2

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)

    def parse_detail(self, response):
        item = response.meta['item']

        item['description'] = response.xpath('//meta[@property="og:description"]/@content').extract_first()
        item['original_image_url'] = [response.xpath('//meta[@property="og:image"]/@content').extract_first()]
        item['image_urls'] = item['original_image_url']

        yield item
