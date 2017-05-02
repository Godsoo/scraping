'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5188
'''

import json
from scrapy.spider import Spider
from scrapy.http import Request
from product_spiders.items import ProductLoaderWithoutSpaces as ProductLoader, Product
from w3lib.url import add_or_replace_parameter
from decimal import Decimal


class AsdaDirect(Spider):
    name = 'e-bedding-asdadirect'
    allowed_domains = ['direct.asda.com']
    start_urls = (
        'http://direct.asda.com/george/home-garden/bedding/D26M04G04C02,default,sc.html',
        'http://direct.asda.com/george/home-garden/duvets/D26M04G04C14,default,sc.html',
        'http://direct.asda.com/george/home-garden/mattresses/D26M04G04C10,default,sc.html',
        'http://direct.asda.com/george/home-garden/pillows/D26M04G04C07,default,sc.html'
        )
    
    def parse(self, response):
        prod_count = response.xpath('//span[@class="pagingcount"]/text()').re("[0-9]+")
        if prod_count:
            for page in range(1, int(prod_count.pop())/20 + 1):
                yield Request(add_or_replace_parameter(response.url, 'start', page * 20))
        
        for url in response.css('.headerContent ::attr(href)').extract():
            yield Request(response.urljoin(url))
            
        for url in response.css('.itemName ::attr(href)').extract():
            yield Request(response.urljoin(url), self.parse_product)
    
    def parse_product(self, response):
        if response.css('input#product_page_type::attr(value)').extract_first() == "Product Set":
            for request in self.parse(response):
                yield request
            return

        category = response.css('#navBreadcrumbs a::text').extract()[2:]
        identifiers = response.xpath('//input[@id="product_code_string"]/@value').extract_first().split('|')
        if not identifiers:
            self.log.warning('No identifiers on %s' %response.url)
            return
        prices = response.css('input#item_prices::attr(value)').extract_first().split('|')
        names = response.css('input#product_name_string::attr(value)').extract_first().split('|')
        stocks = response.css('input#item_available::attr(value)').extract_first().split('|')
        data = response.css('script::text').re('(.*"variations".*);')
        if data:
            data = json.loads(data[0])
        
        for n, identifier in enumerate(identifiers):
            loader = ProductLoader(Product(), response=response)
            if stocks[n] == 'OutOfStock':
                if data:
                    continue
                else:
                    loader.add_value('stock', 0)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', identifier)
            loader.add_value('url', response.url)
            loader.add_value('name', names[n])
            if data:
                loader.add_value('name', data['variations'][identifier].values())
            loader.add_value('price', prices[n])
            loader.add_value('category', category)
            loader.add_css('image_url', 'img.singleImage::attr(src)')
            loader.add_xpath('brand', '//meta[@itemprop="brand"]/@content')
            if Decimal(prices[n]) < 200:
                loader.add_value('shipping_cost', '2.95')   
            yield loader.load_item()
            