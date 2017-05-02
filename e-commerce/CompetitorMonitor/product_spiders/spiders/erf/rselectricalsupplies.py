'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5486
'''

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.lib.schema import SpiderSchema


class RSElectricalSupplies(CrawlSpider):
    name = 'erf-rselectricalsupplies'
    allowed_domains = ['rselectricalsupplies.co.uk']
    start_urls = ['http://www.rselectricalsupplies.co.uk/']
    
    categories = LinkExtractor(restrict_css='div#sub_navigation div.d_block, div#categories, div#sub_categories')
    products = LinkExtractor(restrict_css='div#product_listing, div.offer_block', deny='quickview.quickviewid')
    
    rules = (Rule(categories),
             Rule(products, callback='parse_product'))
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        sku = response.xpath('//span[@itemprop="identifier"]/@content').re_first('mpn:(.+)')
        identifier = response.xpath('//input[@id="prod_id"]/@value').extract_first()
        if not identifier:
            loader.add_value('stock', 0)
            identifier = response.xpath('//script/text()').re_first("ecomm_prodid:.+?'(.+)'")
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/span[@itemprop="name"]/text()')
        loader.add_css('price', 'div#current_price span.exc_vat::text')
        loader.add_value('sku', sku)
        category = response.xpath('//div[@id="breadcrumb"]//span[@itemprop="title"]/text()').extract()[-4:-1]
        loader.add_value('category', category)
        loader.add_xpath('image_url', '//img[@itemprop="image"]/@src')
        loader.add_xpath('brand', '//span[@itemprop="brand"]/text()')
        if loader.get_output_value('price') < 60:
            loader.add_value('shipping_cost', '5.50')
        yield loader.load_item()
