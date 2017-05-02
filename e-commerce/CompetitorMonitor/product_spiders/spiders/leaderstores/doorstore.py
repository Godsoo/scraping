"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5176
"""

import re
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product
from w3lib.url import add_or_replace_parameter

def add_vat_to_url(url):
    return add_or_replace_parameter(url, 'v', 'y')


class DoorStore(CrawlSpider):
    name = 'leaderstores-doorstore'
    allowed_domains = ['doorstore.co.uk']
    start_urls = ['http://www.doorstore.co.uk/']
    
    categories = LinkExtractor(allow='/products/')
    products = LinkExtractor(allow='/product/', process_value=add_vat_to_url)
    
    rules = (
        Rule(categories),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response) 
        identifier = re.search('\d\d\d\d', response.url).group(0)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//header[@class="prodCat"]/h1/text()')
        category = response.css('.bread li a::text').extract()[1:]
        category += response.css('.bread li:last-child::text').extract()
        loader.add_value('category', category)
        image_url = response.css('.detimg a::attr(href)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        item = loader.load_item()
        
        options = response.css('.tbl').xpath('.//*[@class="tr"]')
        if not options:
            item['price'] = 0
            yield item
            return
        for option in options:
            loader = ProductLoader(Product(), selector=option)
            loader.add_value(None, item)
            identifier = option.xpath('.//input/@name').extract_first()
            loader.replace_value('identifier', identifier)
            loader.replace_value('sku', identifier)
            loader.replace_css('price', '.tc-price .pr-now::text')
            loader.add_css('price', '.tc-price::text')
            loader.replace_css('name', '.tc-title::text')
            yield loader.load_item()
