"""
Red Hot Sunglasses
Sunglasses Shop
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4911
"""

from scrapy.spider import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import re
import json

class SunglassesShop(CrawlSpider):
    name = "redhotsunglasses-sunglassesshop"
    allowed_domains = ['sunglasses-shop.co.uk']
    start_urls = ['https://www.sunglasses-shop.co.uk/']
    
    categories = LinkExtractor(restrict_css='.mm2fullvertlist, .mmdrop, .PVBoxLink')
    pages = LinkExtractor(restrict_css='.PContainer')
    products = LinkExtractor(restrict_css='.PVBoxTitle')
    alters = LinkExtractor(restrict_css='#alternativeColourProductsCarousel')
    
    rules = [
        Rule(categories),
        Rule(pages),
        Rule(products, callback='parse_product', follow=True),
        Rule(alters, callback='parse_product', follow=True)
        ]
    
    def parse_product(self, response):
        p = re.compile('window.universal_variable =(.+);', re.DOTALL)
        data = response.xpath('//script/text()').re(p)
        try:
            data = json.loads(data[0])['product']
        except:
            self.logger.warning('No data on %s' %response.url)
            return
        loader = ProductLoader(item=Product(), response=response)
        name = response.css('.brandProductDetails::text').extract_first().strip() or ' '.join((data['brand'], data['name'], data['color']))
        loader.add_value('name', name)
        for field in ('category', 'brand', 'stock'):
            loader.add_value(field, data[field])
        loader.add_value('identifier', data['id'])
        loader.add_value('url', response.url)
        loader.add_value('price', data['unit_sale_price'])
        loader.add_value('sku', data['sku_code'])
        loader.add_xpath('image_url', '//div[@id="productImageCarousel"]//img/@src')
        yield loader.load_item()
        
        