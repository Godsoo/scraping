'''
Original ticket: https://app.assembla.com/spaces/competitormonitor/tickets/5272
'''

import os
from urlparse import urljoin
from urllib import pathname2url
from w3lib.url import add_or_replace_parameter

from scrapy.spiders import CSVFeedSpider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class Crealytics(CSVFeedSpider):
    name = 'crealytics-crealytics'
    allowed_domains = ['matchesfashion.com']
    start_urls = [urljoin('file:', 
                          pathname2url(os.path.join(HERE, 'crealytics_products.csv')))]
    
    def parse_row(self, response, row):
        yield Request(add_or_replace_parameter(row['URL'], 'country', 'GBR'),
                      self.parse_product)
        
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.css('input.baseProductCode::attr(value)').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        name = response.css('h1.pdp-headline span.pdp-description::text').extract_first()
        loader.add_value('name', name)
        loader.add_css('price', 'p.pdp-price::text')
        category = response.css('div#breadcrumb a::text').extract()[:-1]
        category = [cat.strip() for cat in category]
        if 'Designer' in category:
            category.remove('Designer')
        loader.add_value('category', category)
        image_url = response.xpath('//@data-main-img-url').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        brand = response.css('h1.pdp-headline a::text').extract_first()
        loader.add_value('brand', brand)
        stock = response.xpath('//@data-stl-json').re('%s.+?stockLevelCode":"(.+?)"' %identifier)
        if stock and 'inStock' not in stock:
            loader.add_value('stock', 0)     
        yield loader.load_item()
        