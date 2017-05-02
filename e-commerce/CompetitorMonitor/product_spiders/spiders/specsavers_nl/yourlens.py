'''
Specsavers NL Your Lens
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5102
'''

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader


class YourLens(CrawlSpider):
    name = 'specsavers_nl-yourlens'
    allowed_domains = ['yourlenses.nl']
    start_urls = ['https://www.yourlenses.nl/lenses']
    
    products = LinkExtractor(restrict_css='.product-list-item')
    pages = LinkExtractor(restrict_css='.prodList-pagination :not(.disabled)')
    
    rules = (
        Rule(pages),
        Rule(products, callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(Product(), response=response)
        identifier = response.xpath('//input[@id="prodid"]/@value').extract_first()
        if not identifier:
            self.logger.warning('No identifier for %s' %response.url)
            return
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_css('name', 'div.infotitle h1::text')
        loader.add_css('price', '.inline.price::text')
        loader.add_value('sku', identifier)
        image_url = response.css('.photo::attr(src)').extract_first()
        if image_url:
            loader.add_value('image_url', response.urljoin(image_url))
        brand = response.xpath('//meta[@itemprop="brand"]/@content').extract_first()
        if not brand:
            try:
                brand = response.xpath('//script/text()').re('"manufacturer":"(.*?)"')[0].decode('unicode-escape')
            except IndexError:
                pass
        loader.add_value('brand', brand)
        yield loader.load_item()