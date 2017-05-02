import re
import json

import itertools

from scrapy import Spider
from scrapy.http import Request, FormRequest

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


from product_spiders.lib.schema import SpiderSchema


class OverstockSpider(Spider):
    name = 'bushindustries-overstock.com'
    allowed_domains = ['overstock.com']

    user_agent = 'spd'

    start_urls = ('https://www.overstock.com/Home-Garden/Furniture/32/dept.html?TID=TN:Furn',)

    def start_requests(self):
        yield Request('https://www.overstock.com/intlcountryselect?proceedasus=true&referer=', callback=self.parse_country)

    def parse_country(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        categories = response.xpath('//div[@class="featured-tile"]/a/@href').extract()
        categories += response.xpath('//div[@class="categories"]//a[@class="refinement-link"]/@href').extract()
        categories += response.xpath('//div[h4/a[text()="Furniture"]]//a/@href').extract()
        for url in categories:
            yield Request(response.urljoin(url))

        products = response.xpath('//div[@class="product-info"]//a[div[contains(@class, "product-title")]]/@href').extract()
        products = [response.urljoin(product).split('?refccid')[0] for product in products]
        for product in products:
            yield Request(product, callback=self.parse_product)

        next_url = response.xpath('//div[@class="next-btn"]/a/@href').extract()
        if next_url and products != response.meta.get('products', None):
            next_url = response.urljoin(next_url[0].strip())
            yield Request(next_url, meta={'products': products})

    def parse_product(self, response):
        categories = response.xpath('//ul[@class="breadcrumbs"]//a/span/text()').extract()[-3:]
        name = response.xpath('//*[@itemprop="name"]/h1/text()').extract()[0]
        identifier = re.findall('productId = "(\d+)', response.body)[0]

        spider_schema = SpiderSchema(response)
        product = spider_schema.get_product()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier)
        loader.add_value('url', response.url)
        loader.add_value('name', name)
        loader.add_value('category', categories)
        loader.add_value('image_url', product['image'])
        loader.add_value('brand', product.get('brand', ''))
        loader.add_value('sku', product.get('mpn', ''))
        price = product['offers']['properties'].get('price', None)
        if price:
            loader.add_value('price', price)
        else:
            loader.add_value('price', 0)

        stock = 'InStock' in product['offers']['properties']['availability']
        if not stock:
            loader.add_value('stock', 0)

        item = loader.load_item()

        options = re.findall('options = (.*);', response.body)
        option_selector = response.xpath('//div[contains(@class, "options-section")]')
        if options and options[0] != '[]' and option_selector:
            options = json.loads(options[0])
            for option in options:
                loader = ProductLoader(item=Product(item), response=response)
                if option['description'].upper() not in name.upper():
                    loader.add_value('name', name + ' ' + option['description'])
                loader.add_value('identifier', identifier + '-' + str(option['id']))
                loader.add_value('sku', option.get('vendorSku'))
                loader.add_value('price', option['pricingContext']['sellingPriceUnformatted'])
                yield loader.load_item()
        else:
            if not option_selector and not item['price'] and options[0] != '[]':
                try:
                    options = json.loads(options[0])
                    item['price'] = extract_price(options[0]['pricingContext']['sellingPriceUnformatted'])
                except IndexError:
                    self.log('>>> No available price: ' + response.url)
                    item['price'] = 0
            yield item

