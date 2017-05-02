"""
E-Services NL Rhinocamera spider
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4604
"""

from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from scrapy.utils.url import url_query_parameter, url_query_cleaner

class Rhinocamera(CrawlSpider):
    name = "rhinocamera.nl"
    allowed_domains = ["rhinocamera.nl"]
    start_urls = ['http://www.rhinocamera.nl']
    
    rules = (
        Rule(
            LinkExtractor(restrict_xpaths='//div[@id="rc-navbar-collapse"]'),
             ),
        Rule(
            LinkExtractor(restrict_xpaths='//div[contains(@class, "product-grid")]'
            ),
             callback='parse_product'
             )
        )
            
    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h2[@class="product-title"]/text()')
        identifier = url_query_parameter(response.url, 'ProductID')
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        url = url_query_cleaner(response.url, ('ProductName', 'ProductID'))
        loader.add_value('url', url)
        loader.add_xpath('price', '//div[contains(@class, "product-details")]//span[@class="price"]/text()')
        image_url = response.xpath('//img[@class="prodImg"]/@src').extract_first()
        loader.add_value('image_url', response.urljoin(image_url))
        stock = response.xpath('//div[@id="MasterCopy_Instock"]/h4/text()').re('\d+')
        if stock:
            loader.add_value('stock', stock[0])
        else:
            loader.add_value('stock', 0)
        yield loader.load_item()
        
