import scrapy
from ProductsScraper.items import Product
from ProductsScraper.settings import *
import re
import json
import requests

class UnderarmourSpider(scrapy.Spider):
    name = "underarmour"
    start_urls = ["https://www.underarmour.com/en-us/outlet/womens/tops/g/6cl"]

    def parse(self, response):
        products = json.loads(re.search('\"GRID_DATA\"\:(.*)\,[\s]*\"navigation', response.xpath("//script[contains(text(), 'GRID_DATA')]/text()").extract_first().encode("utf-8"), re.M|re.S|re.I).group(1) + '}')["_embedded"]["results"][0]["products"]
        # print len(products)
        offset = 0
        while 1:
            for prod in products:
                item = Product()

                item['Name'] = prod["content"]['shortName']
                item['original_url'] = prod['materials'][0]["_links"]["web:locale"]["href"]
                item['reg_price'] = re.sub('[^\d\.]', '', str(prod['priceRange']["msrp"]["min"]))
                item['sale_price'] = re.sub('[^\d\.]', '', str(prod['priceRange']["base"]["min"]))
                item['website_id'] = 22
                item['category_id'] = 2
                item['description'] = prod["content"]['categoryName']
                item['original_image_url'] = ["http://underarmour.scene7.com/is/image/Underarmour/" + prod['materials'][0]["assets"][0]["image"] + "?template=v65GridLarge&$size=599,735&$wid=281&$hei=345&$extend=0,220,0,0"]
                item['image_urls'] = item['original_image_url']

                yield item
                
            if len(products) < 60:
                break
            offset = offset + len(products)
            products = json.loads(re.search('\)\]\}\'\,(.*)\,[\s]*\"navigation', requests.get("https://www.underarmour.com/en-us/api/json-grid/outlet/womens/tops/g/6cl?s=&q=&p=&offset=%d&limit=60&stackId=other_grid_header&stackIdx=0&t[IsNewLoadMoreGrid]=0" % offset, headers={'X-Requested-With': "XMLHttpRequest"}).text.encode("utf-8"), re.M|re.S|re.I).group(1) + '}')["_embedded"]["results"][0]["products"]
            if len(products) == 0:
                break
            # break
