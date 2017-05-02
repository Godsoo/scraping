from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import json


class DansononlineSpider(CrawlSpider):
    name = u'dansononline.co.uk'
    allowed_domains = [u'dansononline.co.uk']
    start_urls = [
        u'https://dansononline.co.uk/',
    ]
    rules = (
        Rule(LinkExtractor(allow=('/product-category/', '/brand/'), deny=('add-to-cart', 'add_to_wishlist')), callback='parse_category', follow=True),
        )

    def parse_category(self, response):
        for product in response.css('.products').xpath('li'):
            brand = product.css('.wb-posted_in a::text').extract_first()
            url = product.xpath('a/@href').extract_first()
            yield Request(url, callback=self.parse_product, meta={'brand': brand})
            
    def parse_product(self, response):
        identifier = response.xpath('//div[@itemscope]/@id').re('product-(.+)')
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        category = response.css('.breadcrumb a::text').extract()[1:]
        loader.add_value('category', category)
        loader.add_value('brand', response.meta['brand'])
        loader.add_xpath('image_url', '//div/@data-original-img')
        loader.add_value('identifier', identifier)
        product = loader.load_item()
        if not response.css('.variations'):
            yield product
            return
        
        variations = response.xpath('//form/@data-product_variations').extract_first()
        variations = json.loads(variations)
        for variation in variations:
            variation_loader = ProductLoader(item=Product(product), response=response)
            attributes = variation['attributes'].values()
            variation_loader.replace_value('name', product['name'])
            for attribute in attributes:
                variation_loader.add_xpath('name', '//option[@value="%s"]/text()' %attribute)
            variation_loader.replace_value('price', variation['display_price'])
            variation_loader.replace_value('identifier', variation['variation_id'])
            yield variation_loader.load_item()