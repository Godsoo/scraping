'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5105
'''

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader

from product_spiders.spiders.specsavers_nz.specsaversitems import SpecSaversMeta


class Lensplaza(CrawlSpider):
    name = 'specsavers_nl-lensplaza'
    allowed_domains = ['lensplaza.com']
    start_urls = ['https://www.lensplaza.com/nl_nl/']
    
    categories = LinkExtractor(restrict_css='#nav')
    products = LinkExtractor(restrict_css='.products-grid, .products-list')
    
    rules = (
        Rule(categories),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//input[@name="product"]/@value').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        image_url = response.xpath('//img[@id="image"]/@src').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_xpath('brand', '//*[@itemprop="brand"]/text()')  
        item = loader.load_item()

        promotion = response.xpath('//div[@id="advantages-of-registering-popup"]//p[contains(text(), "korting")]/text()').extract()
        promotion = promotion[0].strip() if promotion else ''
        
        for option in response.xpath('//table[@id="product-option-packages"]/tbody/tr'):
            loader = ProductLoader(Product(), selector=option)
            loader.add_value(None, item)
            identifier = option.xpath('.//@data-id').extract_first()
            loader.replace_value('identifier', identifier)
            loader.add_xpath('name', './/label/text()')
            price = option.css('.price::text').extract()
            loader.replace_value('price', price.pop())
            loader.replace_value('sku', identifier)

            metadata = SpecSaversMeta()
            metadata['promotion'] = promotion
            item = loader.load_item()
            item['metadata'] = metadata
            yield item
