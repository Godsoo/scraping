import json
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class FeneticWellbeing(CrawlSpider):
    name = 'betterlife_healthcare-feneticwellbeing'
    allowed_domains = ['feneticwellbeing.com']
    start_urls = ['http://www.feneticwellbeing.com/']

    categories = LinkExtractor(allow='/product-category/')
    products = LinkExtractor(allow='/shop/')
    
    rules = (Rule(categories),
             Rule(products, callback='parse_product'))
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//input[@name="product_id"]/@value').extract_first() or response.xpath('//input[@name="add-to-cart"]/@value').extract_first()
        if not identifier:
            loader.add_value('stock', 0)
            identifier = response.xpath('//div[@itemtype="http://schema.org/Product"]/@id').re_first('product-(\d+)')
        loader.add_value('identifier', identifier)
        loader.add_css('sku', 'span.sku::text')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_css('price', '.product-price-exvat span.amount::text')
        loader.add_css('price', '.product-price span.amount::text')
        category = response.xpath('//span[@class="posted_in"][contains(., "Categories:")]/a/text()').extract_first()
        loader.add_value('category', category)
        loader.add_css('image_url', 'div.single-product-main-image a::attr(href)')
        brand = response.xpath('//span[@class="posted_in"][contains(., "Brands:")]/a/text()').extract_first()
        loader.add_value('brand', brand)
        item = loader.load_item()
        
        variations = response.xpath('//@data-product_variations').extract_first()
        if not variations:
            yield item
            return
        variations = json.loads(variations)
        for variant in variations:
            loader = ProductLoader(Product(), response=response)
            loader.add_value(None, item)
            loader.replace_value('identifier', variant['variation_id'])
            loader.replace_value('sku', variant['sku'])
            loader.replace_value('price', variant['display_price'])
            if variant['image_link']:
                loader.replace_value('image_url', variant['image_link'])
            loader.add_value('name', variant['attributes'].values())
            yield loader.load_item()