'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5103
'''

from w3lib.url import url_query_cleaner
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader


class LensExpress(CrawlSpider):
    name = 'specsavers_nl-lensexpress'
    allowed_domains = ['lensexpress.nl']
    start_urls = ['https://www.lensexpress.nl/']
    
    categories = LinkExtractor(restrict_css='.category')
    products = LinkExtractor(restrict_css='.title')
    pages = LinkExtractor(allow='/pagina/')
    
    rules = (
        Rule(categories),
        Rule(pages),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.css('input.productId::attr(value)').extract_first()
        loader.add_value('identifier', identifier)
        loader.add_value('url', url_query_cleaner(response.url))
        loader.add_css('name', '.title h1::text')
        category = response.css('.breadcrumbs a::text').extract()
        loader.add_value('category', category[2:])
        image_url = response.css('.productDetail1 .image img::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        loader.add_value('brand', category[-1])  
        item = loader.load_item()
        
        for option in response.xpath('//div[@id="valStaffelSelection"]//li'):
            loader = ProductLoader(Product(), selector=option)
            loader.add_value(None, item)
            identifier = item['identifier'] + '-' + option.xpath('input/@value').extract_first()
            loader.replace_value('identifier', identifier)
            url = item['url'] + '?' + option.xpath('@class').extract_first()
            loader.replace_value('url', url)
            loader.add_css('name', 'span.label::text')
            price = option.css('div.price::text').extract()
            loader.replace_value('price', price.pop())
            loader.replace_value('sku', identifier)
            yield loader.load_item()
            