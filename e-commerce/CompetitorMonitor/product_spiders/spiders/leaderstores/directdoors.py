"""
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5175
"""

import hashlib
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product


class DirectDoors(CrawlSpider):
    name = 'leaderstores-directdoors'
    allowed_domains = ['directdoors.com']
    start_urls = ['https://www.directdoors.com/']
    
    categories = LinkExtractor(restrict_css='.main-sub-nav, .category-link, .paginator')
    products = LinkExtractor(restrict_css='.product')
    
    rules = (
        Rule(categories),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        sku = response.xpath('//div[@itemprop="description"]/div/div[last()]/text()').extract_first()
        loader.add_value('identifier', sku)
        loader.add_value('sku', sku)
        category = response.css('.breadcrumbs a::text').extract()[1:]
        category += response.css('.breadcrumbs li:last-of-type::text').extract()
        loader.add_value('category', category)
        image_url = response.css('img.gallery-main-image::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        if not response.css('.in-stock'):
            loader.add_value('stock', 0)       
        item = loader.load_item()
        
        options = response.css('table.product-table tbody tr')
        for option in options:
            loader = ProductLoader(Product(), selector=option)
            loader.add_value(None, item)
            sku = option.css('span.product-code::text').re('\((.+)\)')[0]
            name = option.css('span.product-name::text').extract_first()
            identifier = '-'.join((sku, hashlib.md5(item['name'] + name).hexdigest()))
            loader.replace_value('identifier', identifier)
            loader.replace_value('sku', sku)
            loader.add_css('price', 'span.product-price-rrp')
            price = option.css('td.product-price').xpath('text()[last()]').extract_first()
            loader.replace_value('price', price)
            if name not in item['name']:
                loader.add_value('name', name)
            yield loader.load_item()
            