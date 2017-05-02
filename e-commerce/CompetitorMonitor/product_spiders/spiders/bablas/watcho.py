"""
Original ticket: https://app.assembla.com/spaces/competitormonitor/tickets/5263
"""

import re

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class WatchO(CrawlSpider):
    name = 'bablas-watcho'
    allowed_domains = ['watcho.co.uk']
    start_urls = ('http://www.watcho.co.uk/watches.html',
                  'http://www.watcho.co.uk/Clocks.html')
    
    categories = LinkExtractor(restrict_css='div.SubCategoryListGrid',
                               restrict_xpaths='//a[@href="%s" or @href="%s"]/following-sibling::*' %start_urls)
    pages = LinkExtractor(restrict_css='div.CategoryPagination')
    products = LinkExtractor(restrict_css='div.ProductDetails')
    
    rules = (Rule(categories),
             Rule(pages),
             Rule(products, callback='parse_product'))
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//input[@name="product_id"]/@value').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        category = response.xpath('//div[@id="ProductBreadcrumb"]//a/text()').extract()[1:]
        loader.add_value('category', category)
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        loader.add_xpath('brand', '//div[@itemtype="http://schema.org/Organization"]/meta[@itemprop="name"]/@content')
        if not response.xpath('//link[@itemprop="availability"]/@href[contains(., "InStock")]'):
            loader.add_value('stock', 0)
        
        sku = identifier
        name = loader.get_output_value('name')
        name_end = re.search('\S+$', name).group(0).strip(' ()')
        keywords = response.xpath('//meta[@name="keywords"]/@content').extract_first().split(',')
        keywords = [word.strip() for word in keywords if word]
        shortest_keyword = min(keywords, key=len) if keywords else 'none'
        from_name = re.findall('\S*\d+\S*', name)
        if shortest_keyword.lower() == name_end.lower():
            sku = name_end
        elif shortest_keyword.upper() == shortest_keyword:
            sku = shortest_keyword
        elif name_end.upper() == name_end:
            sku = name_end
        elif from_name:
            sku = max(from_name, key=len)
            if '(' in sku:
                sku = identifier
        loader.replace_value('sku', sku)
        yield loader.load_item()