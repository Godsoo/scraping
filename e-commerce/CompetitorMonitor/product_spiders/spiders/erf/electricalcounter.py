# -*- coding: utf-8 -*-

'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5485
'''

import re
from w3lib.url import url_query_cleaner
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.lib.schema import SpiderSchema


class ElectricalCounter(CrawlSpider):
    name = 'erf-electricalcounter'
    allowed_domains = ['electricalcounter.co.uk']
    start_urls = ['https://www.electricalcounter.co.uk/']
    
    links = LinkExtractor(allow=u'/products/', process_value=lambda url: url.encode('utf8'))
    rules = (Rule(links, callback='parse_product', follow=True),)
    
    def parse_product(self, response):
        schema = SpiderSchema(response)
        pdata = schema.get_product()
        if not pdata:
            return
        
        loader = ProductLoader(Product(), response=response)
        identifier = re.search('/(\d+)$', url_query_cleaner(response.url)).group(1)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_value('name', pdata['name'])
        loader.add_xpath('price', '//span[@id="product_priceExVAT"]/text()')
        loader.add_value('sku', pdata['productID'])
        category = response.css('p.breadcrumb a::text').extract()[-3:]
        loader.add_value('category', category)
        loader.add_value('image_url', pdata.get('image'))
        if pdata['brand'].get('properties'):
            loader.add_value('brand', pdata['brand']['properties']['name'])
        if loader.get_output_value('price') < 90:
            loader.add_value('shipping_cost', '5.25')
        yield loader.load_item()
