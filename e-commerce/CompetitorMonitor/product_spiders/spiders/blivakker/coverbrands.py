"""
Blivakker account
Coverbrands spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4777
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from decimal import Decimal
import json
from w3lib.url import url_query_cleaner

class Coverbrands(CrawlSpider):
    name = "blivakker-coverbrands"
    allowed_domains = ['coverbrands.no']
    start_urls = ['http://www.coverbrands.no/']
    
    rules = (
        Rule(LinkExtractor(restrict_xpaths='//ul[@id="nav"]', restrict_css='.pages')),
        Rule(LinkExtractor(restrict_css='.products-grid', 
                           process_value=url_query_cleaner), callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        css = '.nosto_product .%s ::text'
        loader.add_css('identifier', css %'product_id')
        loader.add_css('sku', css %'product_id')
        for field in ('url', 'name', 'image_url', 'brand'):
            loader.add_css(field, css %field)
        list_price = response.css(css %'list_price').extract_first()
        sales_price = response.css(css %'price').extract_first()
        loader.add_value('price', list_price)
        if 'InStock' not in response.css(css %'availability').extract_first():
            loader.add_value('stock', 0)
        category = response.css(css %'category').extract_first()
        loader.add_value('category', category.split('/')[-1])
        options_data = response.xpath('//script/text()').re('Product.Config.({.+})')
        if not options_data:
            item = loader.load_item()
            if sales_price != list_price:
                item['metadata'] = {'SalesPrice': Decimal(sales_price)}
            yield item
            return
        options_data = json.loads(options_data[0])
        if len(options_data['attributes']) > 1:
            self.log('More than one options attributes found on %s' %response.url)
            return
        price = loader.get_output_value('price')
        name = loader.get_output_value('name')
        sales_price = Decimal(sales_price)
        for option in options_data['attributes'].values()[0]['options']:
            new_price = sales_price + Decimal(option['price'])
            loader.replace_value('price', price + Decimal(option['oldPrice']))
            loader.replace_value('name', name + ' ' + option['label'])
            loader.replace_value('identifier', option['products'][0])
            loader.replace_value('sku', option['products'][0])
            loader.replace_xpath('image_url', '//li[@id="simple-product-image-%s"]/a/@href' %option['products'][0])
            item = loader.load_item()
            if price + Decimal(option['oldPrice']) != new_price:
                item['metadata'] = {'SalesPrice': new_price}
            yield item
        