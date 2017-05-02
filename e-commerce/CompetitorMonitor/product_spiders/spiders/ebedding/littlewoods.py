"""
E-Bedding account
Littlewoods spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4953
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import re
import json

class Littlewoods(CrawlSpider):
    name = 'e-bedding-littlewoods'
    allowed_domains = ['littlewoods.com']
    start_urls = ['http://www.littlewoods.com/home-garden/bedding/e/b/101980.end']
    
    pages = LinkExtractor(allow='pageNumber')
    products = LinkExtractor(allow='.prd$')
    
    rules = [
        Rule(pages),
        Rule(products, callback='parse_product')
        ]
    
    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_xpath('name', '//span[@id="productName"]//text()')
        loader.add_xpath('sku', '//span[@id="productEAN"]/text()[last()]')
        loader.add_xpath('category', '//div[@id="breadcrumb"]/ul/li[position()>1]/a/span/text()')
        loader.add_css('image_url', '.productImageItem ::attr(href)')
        brand = response.css('.brand ::text').extract_first()
        if brand != "null":
            loader.add_value('brand', brand)
        item = loader.load_item()
        
        p = re.compile('stockMatrix = (.+?);', re.DOTALL)
        data = response.xpath('//script/text()').re(p)
        options = json.loads(data[0])
        for option in options:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value(None, item)
            opt_iter = iter(option)
            opt_name = ''
            for attribute in response.css('.skuAttribute'):
                opt_name = opt_iter.next()
                loader.add_value('name', opt_name)
            colour_url = response.xpath('//input[@class="colourImageUrl"][@name="%s"]/@value' %opt_name).extract_first()
            if colour_url:
                loader.replace_value('image_url', 'http://media.littlewoods.com/i/littlewoods/%s?$1064x1416_standard$' %colour_url)
            loader.replace_value('identifier', opt_iter.next())
            stock = opt_iter.next()
            if stock.startswith('Unavailable'):
                continue
            loader.replace_value('stock', int('Out of stock' not in stock))
            loader.replace_value('price', opt_iter.next())
            yield loader.load_item()
        