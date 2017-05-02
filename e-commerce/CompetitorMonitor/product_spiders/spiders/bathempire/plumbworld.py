from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from urlparse import urljoin
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

class MetaData(Item):
    Promotion = Field()

class Plumbworld(BaseSpider):
    name = 'bathempire-plumbworld.co.uk'
    allowed_domains = ['plumbworld.co.uk']
    start_urls = ['http://www.plumbworld.co.uk/']
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@id="primaryDrop"]//a/@href').extract()
        categories += hxs.select('//div[contains(@id, "dropmenu")]//a/@href').extract()
        for url in categories:
            yield Request(urljoin(base_url, url), callback=self.parse_category)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        if not response.url.endswith('0000'):
            yield Request(response.url, callback=self.parse_product, dont_filter=True)

        for url in hxs.select('//section[@class="productsGrid"]//li[@data-pid]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
            
        categories = hxs.select('//div[@id="Secondary"]//a/@href').extract()
        categories += hxs.select('//section[@class="productsGrid"]//a/@href').extract()
        for url in categories:
            yield Request(urljoin(base_url, url), callback=self.parse_category)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('identifier', '//input[@name="PID"]/@value')
        loader.add_xpath('identifier', '//script/text()', re='"id":(.+?),')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('price', '//span[@itemprop="price"]/text()')
        loader.add_xpath('sku', '//div[@class="partNumber"]/text()', re='Code: *(.+)')
        loader.add_xpath('category', '//nav[@id="Breadcrumb"]//a[position()>1]/text()')
        image_url = hxs.select('//div[@id="productImg"]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin(base_url, image_url[0]))
        loader.add_xpath('brand', '//script/text()', re='"brand":"(.+?)"')
        stock = response.css('.stockStatus p::text').re('\d+')
        if not stock and not response.xpath('//link[@itemprop="availability"]/@href[contains(., "InStock")]'):
            loader.add_value('stock', 0)
        loader.add_value('stock', stock)
        item = loader.load_item()
        if not item['identifier']:
            return
        promotion = hxs.select('//section[@class="pricing"]/p[@class="original"]/span/text()').extract()
        if promotion:
            metadata = MetaData()
            metadata['Promotion'] = ' '.join(s.strip() for s in promotion)
            item['metadata'] = metadata
        yield item

        option_ids = hxs.select('//select[@name="NewProductID"]/option/@value').extract()
        for option_id in option_ids:
            url = response.url.replace(item['identifier'], option_id)
            yield Request(url, callback=self.parse_product, meta={'option': True})
