'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5340
'''

import os
from urlparse import urljoin
from urllib import pathname2url
from w3lib.url import add_or_replace_parameter

from scrapy.spiders import CSVFeedSpider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class RapidOnline(CSVFeedSpider):
    name = 'rapidonline-rapidonline'
    allowed_domains = ['rapidonline.com']
    start_urls = [urljoin('file:', 
                          pathname2url(os.path.join(HERE, 'rapid_online.csv')))]
    
    def parse_row(self, response, row):
        loader = ProductLoader(Product(), response=response)
        loader.add_value('identifier', row['Rapid Code'])
        loader.add_value('name', row['Description'])
        loader.add_value('sku', row['Manufactures Code'])
        loader.add_value('brand', row['Brand'])
        loader.add_value('url', row['URL'])
        yield Request(row['URL'], self.parse_product, meta={'loader': loader})
        
    def parse_product(self, response):
        price = response.css('table.product-prices-table td strong::text').extract()
        category = response.xpath('//div[@id="crumbHolder"]//span[@itemprop="title"]/text()').extract()
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()
        loader = response.meta['loader']
        loader.add_value('price', price)
        loader.add_value('category', category)
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        yield loader.load_item()
