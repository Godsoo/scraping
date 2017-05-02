import scrapy
from ProductsScraper.items import Product
from scrapy.selector import Selector
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re
import requests

class ForallmankindSpider(scrapy.Spider):
    name = "7forallmankind"
    start_urls = ["http://www.7forallmankind.com/sale-women/l/254601"]

    def __init__(self):
        self.ajax_url = 'http://www.7forallmankind.com/l/products/254601?PageSize=200&Page=1'

    def parse(self, response):
        products = requests.get(self.ajax_url, headers={'X-Requested-With': 'XMLHttpRequest'}).json()['Products']
        for prod in products:
            item = Product()

            item['Name'] = prod['ModelName']
            item['original_url'] = prod['ProductUrl']
            item['reg_price'] = prod['MaxRegularPrice']
            item['sale_price'] = prod['MinSalePrice']
            item['website_id'] = 12
            item['category_id'] = 2
            item['original_image_url'] = [prod['ProductImageUrl']]
            item['image_urls'] = item['original_image_url']

            yield item
            # break
