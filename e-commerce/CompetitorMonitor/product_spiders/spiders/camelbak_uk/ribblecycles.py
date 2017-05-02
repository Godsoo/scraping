from scrapy.spiders import Spider
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
import json
import itertools


class CamelbakRibbleCycles(Spider):
    name = "camelbak.uk_ribblecycles.co.uk"
    allowed_domains = ['ribblecycles.co.uk']
    download_delay = 1

    def start_requests(self):
        yield Request('http://www.ribblecycles.co.uk/destination/country/switch/country_code/GB/', callback=self.set_currency)
        
    def set_currency(self, response):
        yield Request('http://www.ribblecycles.co.uk/directory/currency/switch/currency/GBP', dont_filter=True)
        
    def parse(self, response):
        yield Request('http://www.ribblecycles.co.uk/camelbak/',
                      callback=self.parse_brand)
        
    def parse_brand(self, response):
        for url in response.xpath('//h2[@class="name"]//a/@href').extract():
            yield Request(response.urljoin(url), 
                          callback=self.parse_product, 
                          errback=lambda failure, url=response.urljoin(url), retries=0: self.retry(failure, url, retries)
                          )
            
        for url in response.xpath('//div[@class="pages"]//a/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_brand)
        
    def parse_product(self, response):
        image_url = response.xpath('//div[@id="product-image"]//@src').extract_first()
        category = response.xpath('//ul[@itemprop="breadcrumb"]//a/text()').extract()[1:]
        category = category if category else ''
        brand = response.xpath('//th[text()="Brand"]/following-sibling::td/text()').extract_first()
        
        product_data = response.xpath('//script/text()').re('var uvTemp.*?({.+});')
        try:
            product_data = json.loads(product_data[0])['product']
        except KeyError:
            return
        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('identifier', product_data['id'])
        product_loader.add_value('sku', product_data['id'])
        product_loader.add_value('name', product_data['name'])
        if image_url:
            product_loader.add_value('image_url', response.urljoin(image_url))
        product_loader.add_value('price', product_data['unit_sale_price'])
        product_loader.add_value('url', product_data['url'])
        product_loader.add_value('brand', brand)
        product_loader.add_value('category', category)
        if not response.xpath('//button[@title="Buy Now"]'):
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()
        
        prices = response.xpath('//script/text()').re('spPrices.+?({.+?})')
        if prices:
            prices = json.loads(prices[0])
        
        config = response.xpath('//script/text()').re(' Product.Config.(.+)\);')
        if config:
            data = json.loads(config[-1])
            baseprice = data['basePrice']
            options = []
            attributes = data['attributes']
            for attribute in response.xpath('//div[@class="product-option"]'):
                if attribute.xpath('.//label[@class="required"]'):
                    attribute_id = attribute.xpath('.//select/@id').re('\d+')
                    options.append(attributes[str(attribute_id[0])]['options'])
            variants = itertools.product(*options)
            for variant in variants:
                item = Product(product)
                item['price'] = baseprice
                for option in variant:
                    item['identifier'] += '-' + option['id']
                    item['sku'] += '-' + option['id']
                    item['name'] += ' ' + option['label'].strip()
                    if prices:
                        product_id = option['products'][0]
                        item['price'] = prices[product_id]
                    else:
                        item['price'] += option['price']
                yield self.yield_product(Product(item))
            return
        
        bundle = response.xpath('//script/text()').re('Product.Bundle\((.+)\);')
        if bundle:
            data = json.loads(bundle[0])
            baseprice = data['basePrice']
            options = next(data['options'].itervalues())['selections']
            for key in options:
                option = options[key]
                item = Product(product)
                item['price'] = baseprice + option['priceValue']
                item['identifier'] += '-' + key
                item['sku'] += '-' + key
                item['name'] += ' ' + option['name'].strip()
                yield self.yield_product(Product(item))
            return
        
        yield self.yield_product(Product(product))
            
    def yield_product(self, product):
        return product
       
    def retry(self, failure, url, retries):
        self.log('Error found while loading %s' %url)
        if retries < 10:
            self.log('Retrying loading %s' %url)
            yield Request(url, dont_filter=True, callback=self.parse_product,
                          meta={'recache': True},
                          errback=lambda failure, url=url, retries=retries+1: self.retry(failure, url, retries))
        else:
            self.log('Gave up retrying %s' %url)        