"""
Red Hot Sunglasses account
Mister Spex spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4914
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from w3lib.url import url_query_cleaner
import demjson
import re
from scrapy.http import Request

class MisterSpex(CrawlSpider):
    name = 'redhotsunglasses-misterspex'
    allowed_domains = ['misterspex.co.uk']
    start_urls = ['https://www.misterspex.co.uk/']
    
    categories = LinkExtractor(restrict_css='#MainNav, .pagination')
    products = LinkExtractor(restrict_css='.productItem', process_value=url_query_cleaner)
    
    rules = [
        Rule(categories),
        Rule(products, callback='parse_product')
        ]

    def parse_product(self, response):
        if 'contact-lenses' in response.url:
            for item in self.parse_lenses(response):
                yield item
            return
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//input[@name="SKU"]/@value')
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_xpath('name', '//ul[@id="Brand"]/li[position()>1]//text()', re='.+')
        loader.add_css('price', '.itemPrice ::text')
        loader.add_xpath('sku', '//span[@itemprop="sku"]/text()')
        category = response.css('.breadcrumb span::text').extract()
        loader.add_value('category', category[1:-1])
        image_url = response.css('.currentImage ::attr(src)').extract_first()
        loader.add_value('image_url', response.urljoin(image_url))
        loader.add_xpath('brand', '//ul[@id="Brand"]/li[2]/strong/text()')
        if response.xpath('//div[@id="Order"]//link/@href[contains(., "OutOfStock")]'):
            loader.add_value('stock', 0)     
        yield loader.load_item()
        
    def parse_lenses(self, response):
        loader = ProductLoader(item=Product(), response=response)        
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h2[@itemprop="name"]/text()')
        category = response.css('.breadcrumb span::text').extract()
        loader.add_value('category', category[1:-1])
        image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()
        loader.add_value('image_url', response.urljoin(image_url))
        loader.add_xpath('brand', '//div[@id="Brand"]/span[@itemprop="brand"]/text()')
        if response.xpath('//link/@href[contains(., "OutOfStock")]'):
            loader.add_value('stock', 0)
        loader.add_xpath('identifier', '//input[@name="SKU"]/@value')
        loader.add_xpath('sku', '//span[@itemprop="sku"]/text()')
        price = response.css('.itemPrice ::text').extract()
        loader.add_value('price', price[-1])
        item = loader.load_item()
        
        p = re.compile('var Bundles =(.+?\]);', re.DOTALL)
        data = response.xpath('//script/text()').re(p)
        if data:
            data = demjson.decode(data[0])
            for option in data:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value(None, item)
                loader.add_value('name', option['strSize'])
                loader.replace_value('identifier', option['productNo'])
                loader.replace_value('sku', option['productNo'])
                loader.replace_value('price', option['price'])
                loader.replace_value('image_url', response.urljoin(option['img']))     
                yield loader.load_item()
            return
        
        yield item
        for url in response.css('#AvialableVariants .variant::attr(href)').extract():
            yield Request(url, self.parse_lenses)

        