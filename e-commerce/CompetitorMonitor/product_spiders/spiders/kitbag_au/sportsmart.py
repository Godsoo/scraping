"""
Sports Mart spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5080
"""

import re

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class SportsMart(CrawlSpider):
    name = 'kitbag_au-sportsmart'
    allowed_domains = ['sportsmart.com.au']
    start_urls = (
        'http://www.sportsmart.com.au/c/soccer-sportswear',
        'http://www.sportsmart.com.au/c/supporter-wear/soccer-supporter-wear',
        'http://www.sportsmart.com.au/c/footwear/football-boots',
        'http://www.sportsmart.com.au/c/footwear/football-boots',
        'http://www.sportsmart.com.au/c/soccer/soccer-balls'
        )
    
    subcategories = LinkExtractor(restrict_xpaths='//heading[text()="CATEGORIES"]/following-sibling::a[@class="selectedfilter"]/following-sibling::a[@style]')
    pages = LinkExtractor(restrict_css='.pages')
    products = LinkExtractor(restrict_css='.producttable', allow='/p/')
    
    rules = (
        Rule(pages),
        Rule(subcategories),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_xpath('price', '//h2[@itemprop="price"]/text()')
        category = response.xpath('//div[@id="breadcrumbs"]/a/text()').extract()
        loader.add_value('category', category[1:-1])
        image_url = response.css('img.productimage::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('shipping_cost', 10)
        
        loader.add_xpath('identifier', '//link[@rel="canonical"]/@href', re='\d+$')
        loader.add_xpath('sku', '//*/text()', re='Product code \#(.+)$')
        if response.xpath("//*[contains(., 'SOLD OUT') or contains(., 'not available to buy online')]"):
            loader.add_value('stock', 0)
        item = loader.load_item()
        
        options = response.xpath('//*[contains(@class, "sizeselect")]')
        if not options:
            yield item
            return
        
        for option in options:
            name = option.xpath('text()').extract_first()
            if not name:
                continue
            data = response.xpath('//span/text()[contains(., "size:%s")]' %name).extract_first().strip()
            sku = re.search('sku:(\d+)', data).group(1)
            if option.css('.sizeselectsoldout'):
                stock = 0
            else:
                stock = re.search('qty:(\d+)', data).group(1)
                if not stock or not int(stock):
                    stock = 1
            loader = ProductLoader(Product(), response=response)
            loader.add_value(None, item)
            loader.add_value('name', name)
            loader.replace_value('identifier', sku)
            loader.replace_value('sku', sku)
            loader.replace_value('stock', stock)
            pr = loader.load_item()
            pr['metadata'] = {'size': name}
            yield pr
