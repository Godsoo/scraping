"""
Specsavers NL account
TopLenzen spider
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4756
"""
from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpacesEU as ProductLoader

class TopLenzen(CrawlSpider):
    name = 'specsavers.nl-toplenzen'
    allowed_domains = ['toplenzen.nl']
    start_urls = ['http://www.toplenzen.nl/categorie/contactlenzen/']
    
    rules = (
        Rule(LinkExtractor(restrict_css='.puu-pgr', 
                           restrict_xpaths='//div[@id="puu-nav"]/div/ul/li[1]')),
        Rule(LinkExtractor(allow='/product/'), callback='parse_product')
        )
    
    def parse_product(self, response):
        loader = ProductLoader(response=response, item=Product())
        base_identifier = response.xpath('//input[@id="productID"]/@value').extract_first()
        loader.add_value('url', response.url)
        base_name = response.css('.puu-led h1::text').extract_first()
        category = response.css('.puu-rbn span::text').extract()
        loader.add_value('category', category[2:])
        image_url = response.css('.puu-vsl img::attr(src)').extract_first()
        loader.add_value('image_url', response.urljoin(image_url))
        loader.add_css('brand', '.puu-brand ::text')
        base_product = loader.load_item()
        
        options = response.css('.puu-ofrs tr')
        for option in options:
            loader = ProductLoader(selector=option, item=Product(base_product))
            name = base_name + ' ' + option.xpath('td[1]/text()').extract_first()
            loader.replace_value('name', name)
            identifier = base_identifier + '-' + option.xpath('td[1]/text()').re('\d+')[0]
            loader.replace_value('identifier', identifier)
            loader.replace_value('sku', identifier)
            loader.replace_css('price', '.puu-prc::text')
            yield loader.load_item()
        if options or not base_identifier:
            return
        loader.add_css('name', '.puu-prd h1::text')
        loader.add_value('identifier', base_identifier)
        loader.add_value('sku', base_identifier)
        loader.add_css('price', '.puu-prc::text')
        yield loader.load_item()
