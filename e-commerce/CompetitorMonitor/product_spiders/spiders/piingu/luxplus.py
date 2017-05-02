"""
Piingu account
Luxplus.dk spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/4995
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from scrapy.utils.response import open_in_browser

class Luxplus(CrawlSpider):
    name = 'piingu-luxplus'
    allowed_domains = ['luxplus.dk']
    start_urls = ['https://www.luxplus.dk/']
    
    categories = LinkExtractor(restrict_xpaths='//*[contains(@class, "top-navigation")]/li[position()<last()]')
    products = LinkExtractor(allow='/produkt/')
    
    rules = (
        Rule(categories, callback='parse_category'),
        )
    
    def parse_category(self, response):
        if response.url == 'https://www.luxplus.dk/':
            return
        category = response.meta.get('link_text')
        for link in self.products.extract_links(response):
            yield Request(link.url, self.parse_product, meta={'category': category})    
     
    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        identifier = response.xpath('//script/text()').re('product_id: (\d+)')
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        name = response.css('.product_display_padding').xpath('*[position()<3]//text()').extract()
        loader.add_value('name', name)
        loader.add_xpath('price', '//span[@id="p_price"]/text()')
        loader.add_value('category', response.meta.get('category'))
        loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')
        loader.add_value('brand', name[0])
        if response.xpath('//meta[@property="og:availability"]/@content').re('out *of *stock'):
            loader.add_value('stock', 0)      
        yield loader.load_item()
