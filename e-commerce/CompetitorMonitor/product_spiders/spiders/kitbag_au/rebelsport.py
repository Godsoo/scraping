"""
KitBag AU Rebel Sport spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/4983
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import json
from w3lib.url import add_or_replace_parameter, url_query_cleaner

def make_variant_url(url):
    return add_or_replace_parameter(url, 'isvariant', 'true')

class RebelSport(CrawlSpider):
    name = 'kitbag_au-rebelsport'
    allowed_domains = ['rebelsport.com.au']
    start_urls = ['http://www.rebelsport.com.au/store/fangear/soccer-football/604']
    
    categories = LinkExtractor(restrict_css='.secondary-menu', 
                               process_value=lambda url: add_or_replace_parameter(url, 'pageSize', '500'))
    pages = LinkExtractor(restrict_css='.pagination')
    products = LinkExtractor(restrict_css='.product', 
                             process_value=lambda url: make_variant_url(url_query_cleaner(url)))
    
    rules = (
        Rule(categories),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        data = response.xpath('//script/text()').re('{\\\\"Variants.+}')[0]
        data = json.loads(data.replace('\\"', '"'))
        variants = data['Variants']
        for variant in variants:
            url = response.urljoin(variant['ProductPLU'])
            yield Request(make_variant_url(url), self.parse_product)
        
        loader = ProductLoader(item=Product(), response=response)
        identifier = response.xpath('//input[@id="ProductPLU"]/@value').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '(//h1[@itemprop="name"]/text())[1]')
        metadata = {}
        for i in xrange(3):
            variant_name = data['Variant%dSelected' %(i+1)]
            if variant_name and variant_name != 'N/A':
                loader.add_value('name', variant_name)
                metadata[data['Variant%dHeader' %(i+1)]] = variant_name
                if 'size' in variant_name.lower():
                    metadata['size'] = variant_name[5:].strip()
        price = response.css('.price-value .currency::text').extract()
        loader.add_value('price', price.pop())
        category = response.css('.breadcrumb a::text').extract()
        loader.add_value('category', category[1:])
        loader.add_css('image_url', '.product-image::attr(src)')
        loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
        loader.add_value('shipping_cost',  '7.95')
        stock = response.css('.product-stock-widget::attr(ng-init)').re('AvailableOnline: (\w+)')[0]
        if stock != 'true':
            loader.add_value('stock', 0)
        item = loader.load_item()
        item['metadata'] = metadata
        yield item
