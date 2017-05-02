"""
Name: effortlessskin.com
Account: Effortless Skin

IMPORTANT!! This spider must run on primary spiders server. This IP is the only one with allowed access to the feed file.
"""

from scrapy.selector import XmlXPathSelector
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.primary_spider import PrimarySpider

class EffortlessSkinSpider(PrimarySpider):
    name = 'effortlessskin.com'
    allowed_domains = ['www.effortlessskin.com']
    start_urls = ('http://www.effortlessskin.com/images/feed_competitormonitor.xml',)

    csv_file = 'effortlessskin_crawl.csv'

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
