import re
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class WexMeta(Item):
    condition = Field()


class CameraJungleSpider(CrawlSpider):
    name = 'wexphotographic-camerajungle.co.uk'
    allowed_domains = ['camerajungle.co.uk']

    start_urls = ['http://www.camerajungle.co.uk']
    
    rules = (
        Rule(LinkExtractor(restrict_css='.main-nav, .f-pagination, .product-lister', deny='\d+/.+/\d+')),
        Rule(LinkExtractor(restrict_css='.product-lister', allow='\d+/.+/\d+'), callback='parse_product', follow=True)
        )

    def parse_product(self, response):
        loader = ProductLoader(response=response, item=Product())
        condition = response.css('.condition span::text').extract_first()
        if 'Used' not in condition.title():
            return
        identifier = response.url.split('/')[-1]
        loader.add_value('identifier', identifier)
        loader.add_xpath('sku', '//script/text()', re='skuCode": *"(.+)?"')
        categories = response.css('.f-breadcrumb a::text').extract()[1:-1]
        loader.add_xpath('brand', '//script/text()', re='manufacturerName": *"(.+)?"')
        loader.add_value('category', categories)
        loader.add_xpath('name', '//script/text()', re='fullProductName": *"(.+)?"')
        loader.add_xpath('price', '//script/text()', re='currentPrice": *([.\d]+)?')
        loader.add_value('url', response.url)
        loader.add_css('image_url', '.f-slideshow img::attr(src)')
        metadata = WexMeta()
        metadata['condition'] = condition
        product = loader.load_item()
        product['metadata'] = metadata
        yield product
