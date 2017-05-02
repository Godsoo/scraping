'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5595
'''

import json
import re
from decimal import Decimal
from w3lib.url import url_query_parameter
from scrapy.spiders import SitemapSpider
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class HollandAndBarrett(SitemapSpider):
    name = 'healthspan-hollandandbarrett'
    allowed_domains = ['hollandandbarrett.com']
    start_urls = ['http://www.hollandandbarrett.com/']
    
    sitemap_urls = ['http://www.hollandandbarrett.com/robots.txt']
    sitemap_rules = [('/shop/product/', 'parse_product')]
    
    products = LinkExtractor(allow='/shop/product/')
    categories = LinkExtractor(allow='/shop/', deny='/shop/product/')
    
    def parse_product(self, response):
        for product in self.products.extract_links(response):
            yield Request(product.url, self.parse_product)
        data = response.xpath('//script/text()[contains(., "window.universal_variable")]').extract_first()
        if not data:
            return
        data = json.loads(re.search('.+?=(.+)', data, re.DOTALL).group(1))
        pdata = data['product']

        loader = ProductLoader(Product(), response=response)
        loader.add_value('identifier', pdata['id'])
        loader.add_value('url', response.urljoin(pdata['url']))
        loader.add_value('name', pdata['name'])
        loader.add_value('name', pdata.get('size'))
        loader.add_value('price', str(pdata['unit_sale_price']))
        loader.add_value('sku', pdata['sku_code'])
        category = response.css('div.crumb').xpath('.//span[@itemprop="name"]/text()').extract()[1:-1][-3:]
        loader.add_value('category', category)
        loader.add_value('image_url', response.urljoin(pdata['thumbnail_url']))
        loader.add_value('stock', pdata['stock'])
        item = loader.load_item()

        options_url = 'http://www.hollandandbarrett.com/browse/json/selectSkuForPDP.jsp?skuId=%s&productId=%s'
        skus = response.xpath('//@data-sku-id').extract()
        if len(skus) > 1:
            for sku in skus:
                url = options_url % (sku, pdata['id'])
                yield Request(url, self.parse_options, meta={'item': Product(item)})
            return
        
        if pdata['unit_sale_price'] < 20:
            item['shipping_cost'] = '2.99'        
        yield item
        
    def parse_options(self, response):
        data = json.loads(response.body)
        identifier = url_query_parameter(response.url, 'productId')
        sku = url_query_parameter(response.url, 'skuId')
        loader = ProductLoader(Product(), response=response)
        loader.add_value(None, response.meta['item'])
        loader.replace_value('identifier', '.'.join((identifier, sku)))
        loader.replace_value('sku', sku)
        loader.replace_value('name', data['skuName'])
        if not data['skuName'].endswith(data['size']) and not data['skuName'].endswith(data['size'].replace(' ', '')):
            loader.add_value('name', data['size'])
        loader.replace_value('image_url', response.urljoin(data['thumbnail_url']))
        loader.replace_value('price', str(data['unit_sale_price']))
        loader.replace_value('stock', data['stock'])
        if Decimal(data['unit_sale_price']) < 20:
            loader.add_value('shipping_cost', '2.99')
        yield loader.load_item()
        