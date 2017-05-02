'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5099
'''

import itertools
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from w3lib.url import add_or_replace_parameter


class YPO(CrawlSpider):
    name = 'findel-ypo'
    allowed_domains = ['ypo.co.uk']
    start_urls = ['http://www.ypo.co.uk/products']
    
    custom_settings = {'COOKIES_ENABLED': False}
    rotate_agent = True
    
    categories = LinkExtractor(restrict_css='.sidebar__categories')
    products = LinkExtractor(allow='/product/detail/')
    pages = LinkExtractor(allow='page=')
    
    rules = (
        Rule(categories, callback='parse_categories', follow=True),
        Rule(pages),
        Rule(products, callback='parse_product')
        )
    
    def parse_categories(self, response):
        yield Request(add_or_replace_parameter(response.url, 'sort', 'PriceLowHigh'))
        
    def parse_product(self, response):
        if 'aspxerrorpath' in response.url:
            yield Request(response.request.meta['redirect_urls'][0], self.parse_product, dont_filter=True)
            return
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//@data-feefo-vendor-ref').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_css('name', 'header.page-title h1::text')
        loader.add_css('price', 'header.product-sidebar__price h2::text')
        loader.add_value('sku', identifier)
        category = response.css('.breadcrumb a::text').extract()
        loader.add_value('category', category[1:-1])
        image_url = response.css('.product-gallery__main-image img::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        stock = response.css('.product-sidebar__stock::text').extract_first()
        if not 'Order Now' in stock.title():
            loader.add_value('stock', 0)       
        item = loader.load_item()
        if 'Discontinued' in stock.title():
            item['metadata'] = {"Discontinued?": "Yes"}
        
        option_types = response.css('.product-sidebar select')
        if not option_types:
            yield item
            return
        
        options = []
        for option_type in option_types:
            options.append(option_type.xpath('option[@value!="Select"]'))
        variants = itertools.product(*options)
        
        for variant in variants:
            loader = ProductLoader(Product(), response=response)
            loader.add_value(None, item)
            identifier = item['identifier']
            for option in variant:
                loader.add_value('name', option.xpath('text()').extract())
                identifier += '-' + option.xpath('@value').extract_first()
            loader.replace_value('identifier', identifier)
            loader.replace_value('sku', identifier)
            option_item = loader.load_item()
            option_item['metadata'] = item.get('metadata', {})
            yield option_item
