"""
Red Hot Sunglasses
Otticanet
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4912
"""

import re
from scrapy.spider import CrawlSpider, Rule
from scrapy import Spider
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class Otticanet(Spider):
    name = 'redhotsunglasses-otticanet'
    alllowed_domains = ['otticanet.com']
    deduplicate_identifiers = True
    '''
    categories = LinkExtractor(restrict_css='.showAllBrands')
    brands = LinkExtractor(restrict_css='.marchio, .nomeMarchio')
    products = LinkExtractor(restrict_css='.productLink')
    
    rules = [
        Rule(categories),
        Rule(brands),
        Rule(products, callback='parse_product', follow=True)
        ]
    '''

    in_stock = (
        'usually ships in 4/5 days',
        'usually ships in 5/7 days',
        'usually ships in 5/10 days'
        )
    
    def start_requests(self):
        yield Request('http://www.otticanet.com/ajax/setClientSettings.cfm?currentUrl=http%3A%2F%2Fwww.otticanet.com%2F&idLingua=10&idValuta=6&isoNazione=GB&tipologia=', self.set_country)
        
    def set_country(self, response):
        yield Request('http://www.otticanet.com/')

    def parse(self, response):
        categories = set()
        for url in response.xpath('//a[@class="marchio"]/@href').extract():
            u = re.search('(http://.*com/en/[a-z--]+/)', url)
            if u:
                categories.add(u.groups()[0])

        for cat in categories:
            yield Request(cat, callback=self.parse_brands)

    def parse_brands(self, response):
        brands = response.xpath('//a[@class="nomeMarchio"]/@href').extract()
        for brand in brands:
            yield Request(brand, callback=self.parse_products)

    def parse_products(self, response):
        products = response.xpath('//a[@class="productLink"]/@href').extract()
        for product in products:
            u = product
            if not product.endswith('/'):
                u += '/'
            yield Request(u, self.parse_product)
        
    def parse_product(self, response):
        suffix = 'GB'
        is_rx = False
        if '/rx-sunglasses/' in response.url:
            suffix = 'A1'
            is_rx = True

        loader = ProductLoader(item=Product(), response=response)
        base_id = response.url.split('/')[-2]
        try:
            int(base_id)
        except ValueError:
            base_id = response.xpath('//input[@checked="checked" and @class="size-select"]/@value')
            if base_id:
                base_id = base_id.extract()[0]
            else:
                base_id = response.xpath('//meta[@itemprop="sku"]/@content').extract()[0]
                base_id = base_id.replace('en', '').replace('GB', '')

        sku = 'en' + base_id + suffix
        loader.add_value('identifier', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1//span[@itemprop="name"]/text()')
        loader.add_xpath('name', '//span[@itemprop="color"]/text()')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_value('sku', sku)
        category = response.xpath('//div[@id="addressbar"]//a/span/text()').extract()
        loader.add_value('category', category[:-1])
        loader.add_css('image_url', '.imgModello ::attr(src)')
        loader.add_css('brand', '.marchioProd ::text')
        stock = response.css('.in-stock-big.hide')
        if stock and stock.xpath('following-sibling::span[1]/text()').extract_first() not in self.in_stock:
            loader.add_value('stock', 0)
        
        rx_options = response.xpath('//label[@class="rx-type"]')
        size_options = response.xpath('//input[@class="size-select"]')

        if not response.xpath('//select[@name="size"]/option') and not rx_options and not size_options:
            loader.add_xpath('name', '//td[contains(., "size:")]/following-sibling::td[1]/text()[1]')
            yield loader.load_item()
        
        item = loader.load_item()
        for option in response.xpath('//select[@name="size"]/option'):
            loader = ProductLoader(item=Product(), selector=option)
            loader.add_value(None, item)
            loader.add_xpath('name', 'text()')
            sku = 'en' + option.xpath('@value').extract_first() + suffix
            loader.replace_value('identifier', sku)
            loader.replace_value('sku', sku)
            yield loader.load_item()

        for option in rx_options:
            rx_type = option.xpath('./@data-idlenterx').extract()[0]
            sku = 'en' + base_id + suffix.replace('1', rx_type)
            loader = ProductLoader(item=Product(), selector=option)
            loader.add_value(None, item)
            loader.add_xpath('name', './strong[1]/text()')
            loader.replace_value('identifier', sku)
            loader.replace_value('sku', sku)
            price = option.xpath('./following-sibling::div//*[@itemprop="price"]/@content').extract()
            loader.replace_value('price', price)
            yield loader.load_item()

        for option in size_options:
            loader = ProductLoader(item=Product(), selector=option)
            loader.add_value(None, item)
            loader.add_xpath('name', './@data-size-label')
            sku = 'en' + option.xpath('@value').extract_first() + suffix
            loader.replace_value('identifier', sku)
            loader.replace_value('sku', sku)
            yield loader.load_item()

        other_options = response.xpath('//ul[@class="gridMixitup"]//*[@itemtype="http://schema.org/Product"]')
        for option in other_options:
            if is_rx or size_options:
                url = option.xpath('.//*[@itemprop="url"]/@content').extract()[0]
                yield Request(url, callback=self.parse_product)
                continue
            self.log('Parsing similar product')
            loader = ProductLoader(item=Product(), selector=option)
            ident = option.xpath('.//*[@itemprop="productID"]/@content').extract()[0]
            ident = 'en' + ident + suffix
            loader.add_value('identifier', ident)
            loader.add_value('sku', ident)
            loader.add_xpath('brand', './/*[@itemprop="brand"]/*[@itemprop="name"]/@content')
            loader.add_value('category', category[:-1])
            loader.add_xpath('url', './/*[@itemprop="url"]/@content')
            loader.add_xpath('image_url', './/*[@itemprop="image"]/@content')
            loader.add_xpath('price', './/*[@itemprop="price"]/@content')
            name = option.xpath('.//*[@itemprop="name"]/@content').extract()[0]
            name += ' ' + option.xpath('./a/div[@class="name"]/text()').extract()[0]
            loader.add_value('name', name)
            yield loader.load_item()