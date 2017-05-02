'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5594
'''
import demjson
import re
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
from lib.schema import SpiderSchema


class Boots(CrawlSpider):
    name = 'healthspan-boots'
    allowed_domains = ['boots.com']
    start_urls = ['http://www.boots.com/en/Pharmacy-Health/']
    
    categories = LinkExtractor(restrict_css='div#guidedNavigation, li.page, li.next',
                               deny='webapp')
    products = LinkExtractor(restrict_css='div.product_item')
    
    rules = (Rule(categories),
             Rule(products, callback='parse_product'))
    
    def parse_product(self, response):
        try:
            pdata = SpiderSchema(response).get_product()
        except:
            self.logger.error('No structured product data on %s' %response.url)
            return
        options = None
        js_line = ''
        for l in response.body.split('\n'):
            if 'variants:' in l:
                js_line = l
                break

        if js_line:
            options = demjson.decode(re.search(r'variants:(.*};)?', js_line).groups()[0][:-2].strip())

        product_loader = ProductLoader(item=Product(), response=response)
        sku = response.css('span.pd_productVariant::text').extract_first()
        product_loader.add_css('sku', 'span.pd_productVariant::text')
        product_loader.add_xpath('identifier', '//input[@name="productId"]/@value')
        product_loader.add_value('url', response.url)
        try:
            product_loader.add_value('name', pdata['name'])
        except KeyError:
            return
        category = response.xpath('//*[@id="breadcrumb"]//a/text()').extract()[1:-1]
        product_loader.add_value('category', category)
        img = response.xpath('//meta[@property="og:image"]/@content').extract()
        if img:
            product_loader.add_value('image_url', response.urljoin(img.pop()))
        price = response.xpath('//p[@class="productOfferPrice"]/text()').extract()[0]
        product_loader.add_value('price', price)
        if product_loader.get_output_value('price') < 45:
            product_loader.add_value('shipping_cost', '3.5')
        brand = response.xpath('//*[@id="brandHeader"]/a/@href').extract()
        if brand:
            brand = brand[0].replace('/en/', '')[:-1]
            if '/' not in brand:
                product_loader.add_value('brand', brand)
        stock = response.xpath('//link[@itemprop="availability"]/@href').extract_first()
        if stock != 'http://schema.org/InStock':
            product_loader.add_value('stock', 0)
        product = product_loader.load_item()

        yield product

        if options:
            for k, val in options.items():
                option_name = k.replace('_', ' ')
                option_product = Product(product)
                option_product['name'] = product['name'] + ' ' + option_name
                option_product['sku'] = val['productCode']
                option_product['identifier'] = val['variantId']
                option_product['price'] = extract_price(val['nowPrice'])
                yield option_product
    
