import scrapy
from ProductsScraper.items import Product
from scrapy.http.request import Request
from ProductsScraper.settings import *
import re
import json
import time

class FarfetchSpider(scrapy.Spider):
    name = "farfetch"
    start_urls = ["https://www.farfetch.com/shopping/women/sale/clothing-1/items.aspx?ffref=lnp_mod7"]

    def parse(self, response):
        ajax_url = 'https://www.farfetch.com/shopping/women/sale/clothing-1/items.aspx?ffref=lnp_mod7&page=%d&format=json'
        page_num = 1
        self.products_num = 180
        while 1:
            yield Request(url=ajax_url % page_num, headers={'X-NewRelic-ID': 'VQUCV1ZUGwIAUVZUAQgA', 'X-Requested-With': 'XMLHttpRequest'}, callback=self.get_products)
            time.sleep(1)
            # break
            if self.products_num < 180:
                break
            page_num = page_num + 1

    def get_products(self, response):
        products = json.loads(response.text)['Products']['List']
        # print len(products)
        self.products_num = len(products)
        for prod in products:
            item = Product()

            item['Name'] = prod['Description']
            item['original_url'] = response.urljoin(prod['ProductUrl'])
            item['reg_price'] = re.sub('[^\d\.]', '', prod['PriceDisplay'])
            item['sale_price'] = re.sub('[^\d\.]', '', prod['PriceSaleDisplay'])
            item['website_id'] = 20
            item['category_id'] = 2
            item['original_image_url'] = [prod['ImageMain']]
            item['image_urls'] = item['original_image_url']
            item['discount'] = re.sub('[^\d\.]', '', prod['PercentageOff'])
            item['brand'] = prod['DesignerName']

            yield Request(url=item['original_url'], callback=self.get_description, meta={'item': item})

    def get_description(self, response):
        item = response.meta['item']
        try:
            item['description'] = response.xpath('//div/p[@itemprop="description"]/text()').extract_first().strip()
        except:
            item['description'] = ''
        yield item  
