from scrapy.spider import BaseSpider
from scrapy.selector import XmlXPathSelector
from scrapy.utils.response import get_base_url
from product_spiders.items \
import Product, ProductLoaderWithNameStrip as ProductLoader 

class EffortlessSkinSpider(BaseSpider):
    name = 'facethefuture-trial-effortlessskin'
    allowed_domains = ['www.effortlessskin.com']
    start_urls = ('http://www.effortlessskin.com/images/feed_competitormonitor.xml',)
    def parse(self, response):
        base_url = get_base_url(response)
        xxs = XmlXPathSelector(response)
        xxs.register_namespace("g", "http://base.google.com/ns/1.0")
        products = xxs.select('//channel/item')
        for product in products: 
            loader = ProductLoader(item=Product(), selector=product)
            loader.add_xpath('url', 'link/text()')
            loader.add_xpath('name', 'title/text()')
            loader.add_xpath('image_url', 'g:image_link/text()')    
            loader.add_xpath('price', 'g:price/text()')
            loader.add_xpath('brand', 'g:brand/text()')
            loader.add_xpath('category', 'g:brand/text()')
            loader.add_xpath('sku', 'g:id/text()')
            loader.add_xpath('identifier', 'g:id/text()')
            yield loader.load_item()
