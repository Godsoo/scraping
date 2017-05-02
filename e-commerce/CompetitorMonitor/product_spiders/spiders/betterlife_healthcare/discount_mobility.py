'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5251
'''

import itertools
from w3lib.url import url_query_cleaner

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price


class DiscountMobility(CrawlSpider):
    name = 'betterlife_healthcare-discount_mobility'
    allowed_domains = ['discount-mobility.co.uk']
    start_urls = ['http://www.discount-mobility.co.uk/']
    
    categories = LinkExtractor(restrict_css=('ul#main_navigation',
                                             'div.catsidemenu_outer',
                                             'table.subcategoreytable'))
    products = LinkExtractor(restrict_css='div#result_prod_div', process_value=url_query_cleaner)
    
    rules = (Rule(categories),
             Rule(products, callback='parse_product'))
    
    options_to_extract = ('Colour',
                          'Colours',
                          'Battery Size',
                          'Upholstery',
                          'Size')
    
    custom_settings = {'COOKIES_ENABLED': False}
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        loader.add_value('url', response.url)
        category = response.css('div.treemenu a::text').extract()[1:]
        loader.add_value('category', category)
        loader.add_css('image_url', 'div#mainimage_holder img::attr(data-zoom-image)')
        identifier = response.xpath('//input[@name="fproduct_id"]/@value').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_css('price', 'li.shelfBnormalprice::text')
        if loader.get_output_value('price') < 100:
            loader.add_value('shipping_cost', 10)
        item = loader.load_item()
        
        attributes = response.css('table.variabletable tr')
        attributes = [attr for attr in attributes if attr.xpath('td[1]/text()').extract_first() in self.options_to_extract]
        options = []
        for attr in attributes:
            options.append(attr.xpath('td/select/option[not(contains(.,"Please Select"))]'))
        variants = itertools.product(*options)
        if not variants:
            yield item
            return
        
        for variant in variants:
            loader = ProductLoader(Product(), response=response)
            loader.add_value(None, item)
            identifier = item['identifier']
            price = item['price']
            for option in variant:
                identifier += '-' + option.xpath('@value').extract_first()
                name_and_price = option.xpath('text()').extract_first().split('(Add')
                loader.add_value('name', name_and_price[0])
                if len(name_and_price) >1:
                    price += extract_price(name_and_price[1])
            loader.replace_value('identifier', identifier)
            loader.replace_value('sku', identifier)
            loader.replace_value('price', price)
            if price >= 100:
                loader.replace_value('shipping_cost', 0)
            yield loader.load_item()
