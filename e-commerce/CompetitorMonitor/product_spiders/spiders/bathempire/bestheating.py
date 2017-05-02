from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from urlparse import urljoin
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class MetaData(Item):
    Promotion = Field()

class BestHeating(BaseSpider):
    name = "best-heating"
    allowed_domains = ['bestheating.com']
    start_urls = ['http://www.bestheating.com/']
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        for url in hxs.select('//div[@id="custommenu"]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(url, callback=self.parse_category)
            
        for url in hxs.select('//h2/a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        if not hxs.select('//div[@class="product-essential"]'):
            yield Request(response.url, callback=self.parse_category, dont_filter=True)
            return
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//meta[@itemprop="sku"]/@content')
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_xpath('name', '//*[@itemprop="name"]/text()')
        loader.add_xpath('price', '//div[@class="product-shop"]//*[@itemprop="offers"]//span[@class="price"]/text()')
        loader.add_xpath('sku', '//meta[@itemprop="sku"]/@content')
        loader.add_xpath('category', '//div[@class="breadcrumbs"]/ul/li[position()>1]/a/span/text()')
        loader.add_xpath('image_url', '//div[@class="product-img-box"]//img[@itemprop="image"]/@src')
        loader.add_xpath('brand', '//td[@class="data brand"]/text()')
        loader.add_value('shipping_cost', 0)
        item = loader.load_item()
        if hxs.select('//p[@class="availability out-of-stock"]') or not item['price']:
            item['stock'] = 0
        promotion = hxs.select('//div[@id="product_info_box"]//p[@class="old-price"]/span/text()').extract()
        if promotion:
            metadata = MetaData()
            metadata['Promotion'] = ''.join(s.strip() for s in promotion)
            item['metadata'] = metadata
        yield item
