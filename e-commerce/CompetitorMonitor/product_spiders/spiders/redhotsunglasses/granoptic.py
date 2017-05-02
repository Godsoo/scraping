"""
Red Hot Sunglasses account
GranOptic spider
Some products with options have different prices
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4913
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import re

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher


def extract_url(value):
    m = re.search("window.open\('(.+?)'", value)
    if m:
        return m.group(1)
    elif value.startswith('http'):
        return value

class GranOptic(CrawlSpider):
    name = 'redhotsunglasses-granoptic'
    allowed_domains = ['granoptic.com']
    start_urls = ['https://www.granoptic.com/setCurrency/GBP']
    
    categories = LinkExtractor(restrict_css='.menu, .pagination')
    products = LinkExtractor(
        restrict_css=('.span9 .block_c_shadow', '.color'),
        tags=('div', 'a'),
        attrs=('onclick', 'href'), 
        process_value=extract_url)
    
    rules = [
        Rule(categories),
        Rule(products, callback='parse_product', follow=True)
        ]
    
    def __init__(self, *args, **kwargs):
        super(GranOptic, self).__init__(*args, **kwargs)
        self.option_items = dict()
        dispatcher.connect(self.idled, signals.spider_idle)
        
    def idled(self, spider):
        if spider != self or not self.option_items:
            return
        request = Request(self.start_urls[0], self.yield_options, dont_filter=True)
        self.crawler.engine.crawl(request, self)
        
    def yield_options(self, response):
        for item in self.option_items.itervalues():
            yield item
        self.option_items = None
    
    def set_currency(self, response):
        yield Request(response.request.headers['Referer'], self.parse_product, dont_filter=True)
  
    def parse_product(self, response):
        if not response.css('.currency_gbp'):
            yield Request('https://www.granoptic.com/setCurrency/GBP', self.set_currency, dont_filter=True)
            return
        if '/contact-lenses/' in response.url:
            for item in self.parse_lenses(response):
                yield item
            return
        loader = ProductLoader(item=Product(), response=response)
        identifier = response.xpath('//input[@name="id_calibre"]/@value').extract()
        loader.add_value('url', response.url)
        loader.add_css('name', '.nombre ::text')
        loader.add_xpath('name', '//p[contains(., "Frame:")]/text()')
        price = response.css('.nombre ~ .precio::text').re('\S+')
        loader.add_value('price', price)
        loader.add_css('category', '.breadcrumb a::text')
        loader.add_css('image_url', '.pag_producto img::attr(src)')
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        item = loader.load_item()
        if len(identifier) == 1:
            yield item
            return
        for option in response.xpath('//input[@name="id_calibre"]'):
            loader = ProductLoader(item=Product(), selector=option)
            loader.add_value(None, item)
            identifier = option.xpath('@value').extract_first()
            loader.replace_value('identifier', identifier)
            loader.replace_value('sku', identifier)
            loader.add_xpath('name', './../following-sibling::td[1]/text()')
            option_item = loader.load_item()
            if not option.xpath('@checked') and self.option_items.get(identifier):
                continue
            self.option_items[identifier] = option_item
            
    def parse_lenses(self, response):
        loader = ProductLoader(item=Product(), response=response)
        identifier = response.xpath('//input[@name="id"]/@value').extract_first()
        id_tipo = response.xpath('//input[@name="id_tipo"]/@value').extract_first()
        if id_tipo:
            identifier += '-' + id_tipo
        loader.add_value('url', response.url)
        loader.add_css('name', '.nombre ::text')
        loader.add_xpath('price', '//*[@itemprop="price"]/text()')
        loader.add_css('category', '.breadcrumb a::text')
        loader.add_css('image_url', '.pag_producto img::attr(src)')
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        yield loader.load_item()        