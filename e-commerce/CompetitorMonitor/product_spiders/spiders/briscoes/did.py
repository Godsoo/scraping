from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from urlparse import urljoin

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class DID(BaseSpider):
    name = "briscoes-did"
    allowed_domains = ['did.ie']
    start_urls = ('http://www.did.ie/',)
    
    def parse(self, response):
        for url in response.xpath('//div[@class="main-menu"]//a/@href').extract():
            yield Request(urljoin(get_base_url(response), url), callback=self.parse_category)
        
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(url, callback=self.parse_category)
            
        for url in hxs.select('//ul[contains(@class, "products-grid")]/li/h2/a/@href').extract():
            yield Request(url, callback=self.parse_product)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        xpath = '//div[@class="nosto_product"]/span[@class="%s"]/text()'
        if not response.xpath('//div[@class="nosto_product"]'):
            for product in self.parse_category(response):
                yield product
            return
        
        loader = ProductLoader(item=Product(), response=response)
        for s in ('name', 'price', 'brand'):
            loader.add_xpath(s, xpath %s)
        loader.add_xpath('identifier', xpath %'product_id')
        loader.add_xpath('sku', '//h6[@class="product-model"]/text()')
        category = hxs.select(xpath %'category').extract()
        if category:
            category.sort()
            loader.add_value('category', category[-1].strip('/').split('/'))
        loader.add_value('shipping_cost', 29.99)
        if 'InStock' not in hxs.select(xpath %'availability').extract():
            loader.add_value('stock', 0)
        item = loader.load_item()
        if 'Ex Display' in item['name']:
            item['metadata'] = {'Ex Display': 'Ex Display'}
        yield item