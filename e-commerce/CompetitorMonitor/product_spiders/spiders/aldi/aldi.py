'''
Client trial spider for Aldi account.
Takes 25 URLs from the feed file.
Extracting price and image url from the site, the rest from file.
'''

import os
from urlparse import urljoin
from urllib import pathname2url
from scrapy.spiders import CSVFeedSpider as Spider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class Aldi(Spider):
    name = 'aldi-aldi'
    allowed_domains = ['aldi.co.uk']
    start_urls = [urljoin('file:', 
                          pathname2url(os.path.join(HERE, 'products.csv')))]
    
    def parse_row(self, response, row):
        loader = ProductLoader(Product(), response=response)
        loader.add_value('identifier', row['Product Sku / Unique Identifier'])
        loader.add_value('name', row['Product Name'])
        loader.add_value('sku', row['Product Sku / Unique Identifier'])
        loader.add_value('brand', row['Brand Name'])
        loader.add_value('url', row['Product URL'])
        loader.add_value('category', row['Category'])
        yield Request(row['Product URL'], self.parse_product, meta={'loader': loader})
        
    def parse_product(self, response):
        price = response.xpath('//script/text()').re_first('"price":([\d.]+?),')
        image_url = response.css('div.js-picture-container::attr(data-original-src)').extract_first()
        loader = response.meta['loader']
        loader.add_value('price', price)
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        yield loader.load_item()
