'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5541
'''

import re
from w3lib.url import url_query_parameter
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.lib.schema import SpiderSchema


class Staples(CrawlSpider):
    name = 'bushindustries-staples'
    allowed_domains = ['staples.com']
    start_urls = ['http://www.staples.com/Furniture-Chairs-Cabinets/cat_SC2']
    
    categories = LinkExtractor(allow='/cat_', restrict_css='div.cat_gallery', restrict_xpaths='//div[@data-category="furniture"]')
    pages = LinkExtractor(restrict_xpaths='//link[@rel="next"]', tags='link')
    products = LinkExtractor(allow='/product_')
    
    rules = (Rule(categories, follow=True, callback='parse_category'),
             Rule(pages, follow=True, callback='parse_category'))

    def parse_category(self, response):
        category = response.css('li.last::text').extract()
        products = response.xpath('//div[@typeof="Product"]')
        for product in products:
            loader = ProductLoader(Product(), selector=product)
            loader.add_xpath('identifier', './/*[@property="url"]/@sku')
            url = product.xpath('.//*[@property="url"]/@href').extract_first()
            loader.add_value('url', response.urljoin(url))
            loader.add_xpath('name', './/*[@property="url"]/text()')
            loader.add_xpath('price', './/*[@property="price"]/text()')
            loader.add_xpath('sku', './/*[@property="url"]/@sku')
            loader.add_xpath('category', '//li[@typeof="v:Breadcrumb"]/a/text()')
            loader.add_value('category', category)
            loader.add_xpath('image_url', './/*[@property="image"]/@content')
            if loader.get_output_value('price') < 50:
                loader.add_value('shipping_cost', '9.95')
            if product.xpath('.//button[starts-with(@id, "outOfStock")]'):
                loader.add_value('stock', 0)
            yield loader.load_item()
            
        if url_query_parameter(response.url, 'pn') or re.search('/cat_.+/.', response.url):
            return
        filters = response.css('ul.filters input::attr(id)').re('^\S{5}$')
        for filt in filters:
            url = response.url + '/' + filt
            yield Request(url, self.parse_category)
        
    def parse_product(self, response):
        product = SpiderSchema(response).get_product()
        if not product:
            return
        loader = ProductLoader(Product(), response=response)
        loader.add_value('identifier', product['sku'])
        loader.add_value('url', response.url)
        loader.add_value('name', product['name'])
        loader.add_value('price', product['offers']['properties']['price'])
        loader.add_value('sku', product['sku'])
        loader.add_xpath('category', '//a[@id="breadCrumbDetails"]/text()')
        loader.add_value('image_url', product['image'])
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', '9.95')
        if product['offers']['properties']['availability'] != 'http://schema.org/InStock':
            loader.add_value('stock', 0)
        yield loader.load_item()