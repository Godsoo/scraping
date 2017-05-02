import scrapy
from ProductsScraper.items import Product
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re
import json
import time

class NinewestSpider(scrapy.Spider):
    name = "ninewest"
    start_urls = ["http://www.ninewest.com/SALE/19397431,default,sc.html?ep_tag=ZT_TOPSALE"]

    def parse(self, response):
        yield Request(url='http://www.ninewest.com/on/demandware.store/Sites-ninewest-Site/default/Token-RequestToken', headers={'X-Requested-With': 'XMLHttpRequest'}, callback=self.get_token)

    def get_token(self, response):
        token = response.text.strip()
        self.products_num = 18
        page_num = 0
        # # e.g. http://www.ninewest.com/SALE/19397431,default,sc.html?start=0&sz=18&search=search&token=wst40ol9uliudndipqe7&returnObject=SearchResults&ajax=true
        ajax_url = 'http://www.ninewest.com/SALE/19397431,default,sc.html?start=%d&sz=18&search=search&token=' + token + '&returnObject=SearchResults&ajax=true'
        while 1:
            yield Request(url=ajax_url % page_num, headers={'X-Requested-With': 'XMLHttpRequest'}, callback=self.get_products)
            time.sleep(1)
            if self.products_num < 18:
                break
            page_num = page_num + 18

    def get_products(self, response):
        products = json.loads(response.text)['response']['searchResults']
        self.products_num = len(products)
        for prod in products:
            item = Product()

            item['Name'] = prod['productName']
            item['original_url'] = prod['url']
            item['reg_price'] = re.sub('[^\d\.]', '', prod['listPrice'])
            item['sale_price'] = re.sub('[^\d\.]', '', prod['minPrice'])
            item['website_id'] = 19
            item['category_id'] = 3
            item['description'] = prod['productDescription']
            item['original_image_url'] = [prod['defaultImage']['productDetailMain']]
            item['image_urls'] = item['original_image_url']

            yield item
