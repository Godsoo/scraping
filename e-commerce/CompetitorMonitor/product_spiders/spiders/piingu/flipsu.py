'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5170
'''

import json
import re
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import Selector
from scrapy.http import Request
from product_spiders.items import ProductLoaderWithoutSpacesEU as ProductLoader, Product
from w3lib.url import add_or_replace_parameter


class Flipsu(CrawlSpider):
    name = 'piingu-flipsu'
    allowed_domains = ['flipsu.dk']
    start_urls = ['https://flipsu.dk/']
    
    categories = LinkExtractor(allow='/kategori/')
    products = LinkExtractor(allow='/produkt/')
    
    rules = (
        Rule(categories, callback='parse_category', follow=True),
        Rule(products, callback='parse_product')
        )
    
    def parse_category(self, response):
        url = response.url
        for parameter in ('lazy', 'scroll', 'si', 'set'):
            url = add_or_replace_parameter(url, parameter, 1)
        yield Request(url, self.parse_pages)
        
    def parse_pages(self, response):
        html = json.loads(response.body)
        selector = Selector(text=html['html'])
        for url in selector.xpath('//@href[contains(., "/produkt/")]').extract():
            yield Request(url, self.parse_product)
        total_sets = int(selector.css('.totalSets::text').extract_first())
        for s in xrange(total_sets):
            url = add_or_replace_parameter(response.url, 'set', s+1)
            yield Request(url, self.parse_pages)
            
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = re.search('-(\d+)\.html', response.url).group(1)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_css('name', 'div.titles h1 ::text')
        loader.add_css('price', '.rprice .value::text')
        loader.add_value('sku', identifier)
        loader.add_xpath('category', '//div[@id="path"]//a[position()>1]/text()')
        loader.add_css('image_url', 'div#image img::attr(src)')
        loader.add_css('brand', 'h1 .brand-name::text')       
        yield loader.load_item()