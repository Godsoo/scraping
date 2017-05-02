"""
Specsavers NL account
VisionDirect spider
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4759
"""
from scrapy.spider import Spider, Rule
from scrapy.http import Request
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from decimal import Decimal
import re

class VisionDirectSpider(Spider):
    name = 'specsavers.nl-visiondirect'
    allowed_domains = ['visiondirect.nl']
    start_urls = ['http://www.visiondirect.nl/lenzen', 'http://www.visiondirect.nl/oogverzorging']
    
    rules = (
        Rule(LinkExtractor(restrict_css='.menu__pa'), callback='parse_product'),
        )
    
    def parse(self, response):
        for url in re.findall('<.+?"products-list__item".+?href="(.+?)"', response.body, re.DOTALL):
            yield Request(url, self.parse_product)

    def parse_product(self, response):
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', re.findall('product_id.+?(\d+)', response.body))
        loader.add_xpath('url', '//link[@rel="canonical"]/@href')
        loader.add_value('name', re.findall('"name":"(.+?)"', response.body))
        prices = re.findall('tier_price_total".+?([\d.]+)', response.body)
        if not prices:
            return
        price = Decimal(prices[0]).quantize(Decimal('.01'))
        loader.add_value('price', price)
        loader.add_value('sku', re.findall('product_id.+?(\d+)', response.body))
        category = re.findall('<span class="technical_label">Lenstype:</span><a href.+?>(.+?)</a', response.body) or re.findall('<span class="technical_label">Producttype:</span><a href.+?>(.+?)</a', response.body)
        loader.add_value('category', category)
        loader.add_value('image_url', re.findall('<img src="(\S+media/catalog/product\S+)"', response.body))
        loader.add_value('brand', re.findall('<span class="technical_label">Merk:</span><a href.+?>(.+?)</a', response.body))
        if loader.get_output_value('price') < 70:
            loader.add_value('shipping_cost', '4.98')
        yield loader.load_item()