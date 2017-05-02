import json
import re
from w3lib.url import add_or_replace_parameter
from scrapy import Spider, Request
from scrapy.linkextractors import LinkExtractor
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class CycleSurgery(Spider):
    name = 'zyro-cyclesurgery'
    allowed_domains = ['cyclesurgery.com']
    start_urls = ['https://www.cyclesurgery.com/api/search/lister/uk/search/new?query=&locale=en&page=1&size=&mainWebShop=cyclesurgery&sort=&filter=']

    categories = LinkExtractor('/c/')
    brands = LinkExtractor('/brands/')
    products = LinkExtractor('/p/')

    def start_requests(self):
        yield Request('https://www.cyclesurgery.com/api/search/lister/uk/search/new?query=&locale=en&page=0&size=48&mainWebShop=cyclesurgery&sort=&filter=',
                      self.parse_json_list,
                      headers = {'Accept': 'application/json, text/plain, */*'})

    def parse_json_list(self, response):
        data = json.loads(response.body)
        for page in xrange(data['totalPages']):
            yield Request(add_or_replace_parameter(response.url, 'page', page),
                          self.parse_json_list,
                          headers = {'Accept': 'application/json, text/plain, */*'})

        for item in data['items']:
            url = 'https://www.cyclesurgery.com/p/tile-%s.%d.html' % (item['productCode'], item['colourId'])
            yield Request(url, self.parse_product)

    def parse(self, response):
        brands_url = response.xpath('//div[@id="navigation"]//a[text()="Brands"]/@href').extract()
        yield Request(response.urljoin(brands_url[0]), callback=self.parse_brands)

        for url in response.xpath('//div[@id="navigation"]//a[@class="level_1"]/@href').extract():
            yield Request(response.urljoin(url), callback=self.parse_main_category)

    def parse_brands(self, response):
        brands = response.xpath('//div[@class="brandbox"]//a/@href').extract()
        for brand in brands:
            url = response.urljoin(brand)
            yield Request(url, callback=self.parse_main_category)
            yield Request(url, callback=self.parse_product_list)
            yield Request(url, callback=self.parse_product)

    def parse_main_category(self, response):
        categories = response.xpath('//ul[@class="sub_navigation_level_3"]//a/@href').extract()
        for url in categories:
            yield Request(url, callback=self.parse_product_list)

    def parse_product_list(self, response):
        for url in response.xpath('//li[@class="next_page"]/a/@href').extract():
            yield Request(url, callback=self.parse_product_list)

        for url in response.xpath('//div[@id="productsList"]//p[@class="product_title"]/a/@href').extract():
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        data = response.xpath('//script[contains(., "var productInfo")]/text()').extract_first()
        data = json.loads(re.search('var productInfo = ({.+);', data).group(1))
        base_id = data['productId']
        sku = data['productCode']
        brand = data['brand']['description']
        prices = response.xpath('//script/text()').re('SITE.data.productPrices."%s". = SITE.dataImporter.({.+}).;' % base_id)
        prices = json.loads(prices[0])
        availabilities = response.xpath('//script/text()').re('SITE.data.productAvailabilities."%s". = SITE.dataImporter.({.+}).;' % base_id)
        availabilities = json.loads(availabilities[0])

        name = response.css('h1.product-details__title--product-detail ::text').re('\S+')

        categories = response.css('div.page-breadcrumb__container').xpath('.//span[@itemprop="name"]/text()').extract()[:-1]

        for colour in data['productColorVariations']:
            if not colour['visible']:
                continue
            colour_id = colour['colorId']
            colour_prices = [col['skus'] for col in prices['colours'] if str(col['colourId']) == colour_id][0]
            if 'colorAvailabilities' in availabilities:
                colour_availabilities = [col['skuAvailabilities'] for col in availabilities['colorAvailabilities'] if str(col['colorId']) == colour_id][0]
            else:
                colour_availabilities = None

            loader = ProductLoader(response=response, item=Product())
            loader.add_value('name', name)
            loader.add_value('category', categories)
            loader.add_value('brand', brand)
            loader.add_value('sku', sku)
            loader.add_value('url', response.url)
            loader.add_value('name', colour['description'])
            loader.add_value('image_url', colour['images'][0]['regularImageUrl'])
            item = loader.load_item()

            for size in colour['sizes']:
                if not size['active']:
                    continue
                loader = ProductLoader(Product(), response=response)
                loader.add_value(None, item)
                loader.add_value('name', size['code'])
                loader.add_value('identifier', size['sku'])
                price = [s['sellPrice'] for s in colour_prices if str(s['skuId']) == size['sku']][0]
                loader.add_value('price', price)
                availability = True
                if colour_availabilities:
                    availability = [s['availability'] for s in colour_availabilities if str(s['skuCode']) == size['sku']][0]
                if availability:
                    yield loader.load_item()
