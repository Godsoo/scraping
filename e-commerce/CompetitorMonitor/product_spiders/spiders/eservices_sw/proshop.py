from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader

class ProShop(BaseSpider):
    name = 'proshop.se'
    allowed_domains = ['proshop.se']
    start_urls = ('https://www.proshop.se/Digitalkamera',
                  'https://www.proshop.se/Mobiltelefon',
                  'https://www.proshop.se/iPad-och-tablet',
                  'https://www.proshop.se/Laptop')
    
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        for url in hxs.select('//ul[@class="pagination"]//a/@href').extract():
            yield Request(urljoin(base_url, url))
        
        for product in hxs.select('//ul[@id="products"]/li'):
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('identifier', './/@data-id')
            url = product.select('.//a/@href').extract()[0].split('?')[0]
            loader.add_value('url', urljoin(base_url, url))
            loader.add_xpath('name', './/@data-name')
            loader.add_value('price', ''.join(product.select('.//@data-price').re('\S')))
            loader.add_xpath('sku', './/@data-id')
            loader.add_xpath('category', '//ol[@id="breadcrumbs"]/li[position()>1]/a/span/text()')
            loader.add_xpath('image_url', './/@src')
            loader.add_xpath('brand', './/@data-brand')
            yield loader.load_item()
            