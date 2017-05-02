"""
Piingu account
Nicehair.dk spider
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/4994
"""

import csv
import os
import itertools
from decimal import Decimal

from product_spiders.config import DATA_DIR
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoaderEU, ProductLoaderWithoutSpaces as ProductLoader

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

HERE = os.path.abspath(os.path.dirname(__file__))

class Nicehair(CrawlSpider):
    name = 'piingu-nicehair'
    allowed_domains = ['nicehair.dk']
    start_urls = ['https://nicehair.dk/']
    
    custom_settings = {'COOKIES_ENABLED': False}
    #download_delay = 1
    #rotate_agent = True
        
    categories = LinkExtractor(restrict_css='.navbar-nav')
    subcategories = LinkExtractor(restrict_css='.filterproducts')
    brands = LinkExtractor(restrict_css='.letterbrands')
    products = LinkExtractor(restrict_css='.product-name')
    
    rules = (
        Rule(categories, callback='parse_category', follow=True),
        Rule(subcategories, callback='parse_category')
        )
    
    def start_requests(self):
        dispatcher.connect(self.start_parse_brands, signals.spider_idle)
        self.brands_parsed = False
        
        for url in self.start_urls:
            yield Request(url)

        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            
            with open(filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'],
                                  self.parse_product,
                                  meta={'category': row['category'].decode('utf-8')})

    def start_parse_brands(self, spider):
        if spider.name == self.name and not self.brands_parsed:
            self.brands_parsed = True
            self.log('Spider idle. Starting to parse brands page')
            request = Request('https://nicehair.dk/m.html', self.parse_brands,
                              dont_filter=True)
            self.crawler.engine.crawl(request, self)

    def parse_brands(self, response):
        for link in self.brands.extract_links(response):
            yield Request(link.url, self.parse_category,
                          meta={'link_text': link.text})
                    
    def parse_category(self, response):
        category = response.meta.get('link_text')
        if response.xpath('//h1/text()').extract_first() == '404':
            retries = response.meta.get('retries', 0)
            if retries < 10:
                yield Request(response.url, self.parse_category,
                              dont_filter=True, meta={
                                  'link_text': category,
                                  'retries': retries+1})
        links = self.products.extract_links(response)
        for link in links:
            yield Request(link.url, self.parse_product, meta={'category': category})
        category_id = response.xpath('//@data-cat').extract_first()
        if not category_id:
            return
        url = 'https://nicehair.dk/catalog/category/ajax-products.php?category_id=%s&offset=%d' %(category_id, len(links))
        yield Request(url, self.parse_category, meta={'link_text': category})
                         
    def parse_product(self, response):
        loader = ProductLoaderEU(item=Product(), response=response)
        identifier = response.xpath('//@data-id').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_xpath('name', '(//h1/text())[1]')
        loader.add_css('price', '.price-including-tax .price ::text')
        if not loader.get_output_value('price'):
            return
        loader.add_value('sku', identifier)
        loader.add_value('category', response.meta.get('category'))
        image_url = response.xpath('//img[@id="image"]/@src').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_xpath('brand', '//strong[text()="Brand:"]/following-sibling::a/text()')
        loader.add_xpath('brand', '//img[contains(@src, "/brands/")]/@title')
        if not response.css('.in-stock').xpath('div[@itemprop="availability"][not (contains(., "Ikke"))]').extract():
            loader.add_value('stock', 0)
            loader.replace_value('price', 0)
        item = loader.load_item()
        option_attributes = response.xpath('//select[@id="bundle-option"]')
        if not option_attributes:
            yield item
            return
        options = []
        for attribute in option_attributes:
            options.append(attribute.xpath('.//option[@value!=""]'))
        variants = itertools.product(*options)
        for variant in variants:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value(None, item)
            identifier = ''
            loader.replace_value('name', '')
            price = item['price']
            for option in variant:
                identifier += '-' + option.xpath('@value').extract_first()
                loader.add_value('name',  option.xpath('text()').extract_first())
                if option.xpath('@disabled'):
                    loader.replace_value('stock', 0)
                extra_cost = option.xpath('@data-extra-cost').extract_first()
                if extra_cost:
                    price += Decimal(extra_cost)
            loader.replace_value('price', price)
            loader.replace_value('identifier', identifier.strip('-'))
            loader.replace_value('sku', identifier.strip('-'))
            yield loader.load_item()
            