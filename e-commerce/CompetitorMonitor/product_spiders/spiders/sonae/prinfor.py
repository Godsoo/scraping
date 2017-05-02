"""
Worten account
Prinfor spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4774
"""

import datetime

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request

from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader
from sonaeitems import SonaeMeta

class PrinforSpider(CrawlSpider):
    name = 'worten-prinfor'
    allowed_domains = ['prinfor.pt']
    start_urls = ['https://www.prinfor.pt/']
    
    custom_settings = {'COOKIES_ENABLED': False}
    
    rules = (
        Rule(LinkExtractor(restrict_css='.pagination')),
        Rule(LinkExtractor(restrict_css='.product_list .product-name'), callback='parse_product')
        )
    
    def start_requests(self):
        yield Request(self.start_urls[0], callback=self.parse_main)
    
    def parse_main(self, response):
        for category in response.css('.cbp-hrmenu-tab')[1:]:
            category_name = category.css('.cbp-tab-title').xpath('text()[normalize-space(.)]').extract_first().strip()
            if category_name == u'Eletrodom\xe9sticos':
                category_name = u'Electrodom\xe9sticos'
            for url in category.xpath('.//@href').extract():
                yield Request(response.urljoin(url), meta={'category': category_name})
                
    def parse(self, response):
        for url in response.css('.pagination ::attr(href)').extract():
            yield Request(response.urljoin(url), meta=response.meta)
        for url in response.css('.product_list .product-name ::attr(href)').extract():
            yield Request(response.urljoin(url), meta=response.meta, callback=self.parse_product)
    
    def parse_product(self, response):
        if not response.xpath('//body[@id="product"]') and not 'body id="product"' in response.body:
            return
        promo_dates = response.xpath('//div[@class="pl_promoinfo_product_promo"]/span[@class="date"]/text()').extract()
        promo_start, promo_end = (None, None)
        try:
            promo_dates = [datetime.datetime.strptime(d, '%d-%m-%Y') for d in promo_dates]
            promo_start, promo_end = promo_dates
        except ValueError:
            pass

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//input[@id="product_page_product_id"]/@value')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        price = response.xpath('//span[@id="our_price_display"]/text()').extract_first()
        loader.add_value('price', price.replace(' ', ''))
        loader.add_xpath('sku', '//span[@itemprop="sku"]/text()')
        loader.add_xpath('sku', '//script/text()', re="productReference='(.+?)'")
        category = response.css('.navigation_page ::attr(title)').extract()
        main_category = response.meta.get('category')
        if not category or category[0].strip() != main_category:
            category = [main_category] + category
        loader.add_value('category', category)
        loader.add_xpath('image_url', '//img[@id="bigpic"]/@src')
        loader.add_xpath('brand', '//a[@itemprop="brand"]/span/text()')
        if not response.css('.primary_block .avail3'):
            loader.add_value('stock', 0)
        metadata = SonaeMeta()
        if promo_start and promo_end:
            metadata['promo_start'] = promo_start.strftime('%Y-%m-%d')
            metadata['promo_end'] = promo_end.strftime('%Y-%m-%d')
        metadata['extraction_timestamp'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        item = loader.load_item()
        item['metadata'] = metadata
        yield item
