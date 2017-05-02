'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5190
'''

import re
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product

class BandQ(CrawlSpider):
    name = 'e-bedding-bandq'
    allowed_domains = ['diy.com']
    start_urls = (
        'http://www.diy.com/rooms/bedroom/bedding/DIY822487.cat',
        'http://www.diy.com/rooms/bedroom/beds-mattresses/DIY822423.cat'
        )
    
    categories = LinkExtractor(restrict_css='#content .menu')
    pages = LinkExtractor(restrict_css='.paginator')
    products = LinkExtractor(restrict_css='#product-listing h3')
    
    rules = (
        Rule(categories),
        Rule(pages),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = re.search('(\d+)_BQ', response.url).group(1)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_css('name', '.product-summary h1.product-title::text')
        loader.add_css('price', '.product-price::attr(content)')
        loader.add_css('sku', 'dl.product-code dd::text')
        loader.add_value('category', 'Bedroom')
        category = response.css('.breadcrumb').xpath('.//li/a/text()').extract()[-1]
        loader.add_value('category', category)
        image_url = response.css('.main-img img::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_xpath('brand', '//th[text()="Brand"]/following-sibling::td/text()')
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', 5)      
        yield loader.load_item()
