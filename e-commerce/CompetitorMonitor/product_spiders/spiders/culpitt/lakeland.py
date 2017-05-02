from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.http import Request

class LakeLand(BaseSpider):
    name = 'culpitt-lakeland'
    allowed_domains = ['lakeland.co.uk']
    start_urls = ['http://www.lakeland.co.uk/in-the-kitchen']
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//div[@class="subnav"]//a[text()="Baking"]/../following-sibling::ul[1]//a/@href').extract()
        for url in categories:
            yield Request(urljoin(base_url, url), callback=self.parse_category)
            
    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//div[contains(@class, "product-list")]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        for url in hxs.select('//ul[@class="pagination"]//a/@href').extract():
            yield Request(urljoin(base_url, url), callback=self.parse_category)
            
    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        if hxs.select('//a[@href="#product-range"]'):
            for url in hxs.select('//section[contains(@class, "product-range")]//div/a/@href').extract():
                yield Request(urljoin(base_url, url), callback=self.parse_product)
            return
        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('name', '//h1[@class="fn c-both"]/text()')
        loader.add_xpath('price', ('//span[@class="cta now-price"]/text()', '0'))
        if not hxs.select('//select[@id="quantity"]'):
            loader.add_value('stock', 0)
        categories = hxs.select('//section[@class="breadcrumbs"]//a/text()').extract()[2:-1]
        if 'in the kitchen' in categories:
            categories.remove('in the kitchen')
        if 'baking' in categories:
            categories.remove('baking')
        loader.add_value('category', categories)
        loader.add_value('brand', "Lakeland")
        loader.add_xpath('identifier', '//meta[@name="productcode"]/@content')
        loader.add_xpath('sku', '//meta[@name="productcode"]/@content')
        loader.add_xpath('image_url', '//img[@class="main-image"]/@src')
        loader.add_value('url', response.url)
        product = loader.load_item()
        if product.get('price', 30) < 30:
            product['shipping_cost'] = 2.99
        yield product
