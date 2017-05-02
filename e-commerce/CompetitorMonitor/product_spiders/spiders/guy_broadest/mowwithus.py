from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy import Selector

from product_spiders.items import ProductLoader, Product

class nowwithusSpider(CrawlSpider):
    download_delay = 6
    name = "mowwithus.com"
    allowed_domains = ["www.mowwithus.com"]
    start_urls = ('http://www.mowwithus.com',)
    
    rules = (
        Rule(LinkExtractor(restrict_xpaths='//ul[@id="nav_ul"]', restrict_css='.PageLink')),
        Rule(LinkExtractor(restrict_css='.product-results'), callback='parse_product')
        )

    def parse_product(self, response):
        name = response.css('.productName').xpath('text()').extract_first()
        html = response.xpath('//script[contains(., "BuyFormPrice")]/text()').re('(<table>.+?</table>)')[0]
        selector = Selector(text=html)
        price = selector.css('.BuyFormPrice').xpath('text()').extract_first()
        url = response.xpath('//link[@rel="canonical"]/@href').extract_first()
        identifier = response.css('.productBuyForm').xpath('@id').re('(.+)_buyForm')
            
        l = ProductLoader(item=Product(), response=response)
        l.add_value('identifier', identifier)
        l.add_value('name', name)
        l.add_value('url', url)
        l.add_value('price', price)
        yield l.load_item()

