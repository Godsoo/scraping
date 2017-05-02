import scrapy
from ProductsScraper.items import Product
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re

class ShopbopSpider(scrapy.Spider):
    name = "shopbop"
    start_urls = ['https://www.shopbop.com/shop-category-sale-clothing/br/v=1/2534374302155173.htm']

    def __init__(self):
        self.baseindex = 0
        self.nextpage_url = 'https://www.shopbop.com/shop-category-sale-clothing/br/v=1/2534374302155173.htm?baseIndex=%d'

    def parse(self, response):
    	products = response.xpath('//div[@class="product-list"]/ul/li//div[@class="info clearfix"]/a[contains(@class, "url")]')
    	if len(products) == 0:
    		return
    	self.baseindex = self.baseindex + len(products)
        for prod in products:
            item = Product()

            item['Name'] = prod.xpath('div[@class="title"]/text()').extract_first().strip()
            item['brand'] = prod.xpath('div[@class="brand"]/text()').extract_first().strip()
            item['original_url'] = response.urljoin(prod.xpath('@href').extract_first())
            item['reg_price'] = re.sub('[^\d\.\,]', '', prod.xpath('.//span[@class="retail-price"]/text()').extract_first()).strip()
            item['sale_price'] = re.sub('[^\d\.\,]', '', prod.xpath('.//span[@class="sale-price"]/span[@class="sale-price-low"]/text()').extract_first()).strip()
            item['website_id'] = 17
            item['category_id'] = 2

            yield Request(item['original_url'], meta={'item': item}, callback=self.parse_detail)
            # break
        # return
        yield Request(self.nextpage_url % self.baseindex, callback=self.parse)

    def parse_detail(self, response):
        item = response.meta['item']

        item['description'] = ' '.join([frag.strip() for frag in response.xpath('//div[@id="detailsAccordion"]/div[@itemprop="description"]//text()').extract()])
        item['original_image_url'] = [response.xpath('//div[@id="productImageContainer"]//img[@id="productImage"]/@src').extract_first()]
        item['image_urls'] = item['original_image_url']

        yield item
