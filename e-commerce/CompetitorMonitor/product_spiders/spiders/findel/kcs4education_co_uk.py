"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5098

Monitor all products.
"""
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import json
from copy import deepcopy


class Kcs4educationSpider(scrapy.Spider):
    name = 'findel-kcs4education.co.uk'
    allowed_domains = ['kcs4education.co.uk']
    start_urls = ('http://www.kcs4education.co.uk/',)

    def parse(self, response):
        for url in response.xpath('//ul[@class="nav-primary"]/li/a/@href').extract():
            yield scrapy.Request(response.urljoin(url + '?limit=48'), callback=self.parse_products)

    def parse_products(self, response):
        for url in response.xpath('//div[@class="pages"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url + '?limit=48'), callback=self.parse_products)

        category = response.xpath('//div[@class="breadcrumbs"]//strong/text()').extract_first()
        products = response.xpath('//div[contains(@class, "products-grid")]/article')
        for product in products:
            options = product.xpath('.//button[@title="More Info"]')
            if options:
                url = product.xpath('./a/@href').extract_first()
                yield scrapy.Request(url, callback=self.parse_products_options, meta={'category': category})
            else:
                identifier = product.xpath('.//span[contains(@id,"price-excluding-tax-")]/@id').extract_first()
                identifier = identifier.replace('price-excluding-tax-', '')
                name = product.xpath('.//h2[@class="product-name"]/a/text()').extract_first()
                url = product.xpath('.//h2[@class="product-name"]/a/@href').extract_first()
                price = product.xpath('.//span[contains(@id,"price-excluding-tax-")]/text()').extract_first()
                sku = product.xpath('.//span[@class="product-sku__value"]/text()').extract_first()
                image_url = product.xpath('./a/img/@src').extract_first()
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('category', category)
                loader.add_value('url', url)
                loader.add_value('image_url', response.urljoin(image_url))
                loader.add_value('price', price)
                option_item = loader.load_item()
                yield option_item

    @staticmethod
    def parse_products_options(response):
        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            category = response.meta.get('category')
            identifier = response.xpath('//input[@name="product"]/@value').extract_first()
            name = response.xpath('//div[@class="product-name"]/span/text()').extract_first()
            price = response.xpath('//span[@id="price-excluding-tax-{}"]/text()'.format(identifier)).extract_first()
            sku = response.xpath('//th[@class="label" and text()="Catalogue Product Code"]/../td/text()').extract_first()
            image_url = response.xpath('//*[@id="image-main"]/@src').extract_first()
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', name)
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('category', category)
            loader.add_value('url', response.url)
            loader.add_value('image_url', response.urljoin(image_url))
            loader.add_value('price', price)
            item = loader.load_item()
            product_data = json.loads(options_config.groups()[0])
            products = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))

            for identifier, option_name in products.iteritems():
                option_item = deepcopy(item)
                option_item['identifier'] += '_' + identifier
                option_item['name'] = name + option_name
                yield option_item
        else:
            for variant in response.xpath('//*[@id="super-product-table"]/tbody/tr'):
                o_id = variant.xpath('.//input/@name').extract_first()
                if not o_id:
                    continue
                o_id = o_id.replace('super_group[', '')[:-1]
                category = response.meta.get('category')
                identifier = response.xpath('//input[@name="product"]/@value').extract_first()
                name = variant.xpath('.//p[@class="name-wrapper"]/text()').extract_first()
                price = variant.xpath('.//span[@class="price" and contains(@id,"price-excluding-tax-")]/text()').extract_first()
                sku = variant.xpath('.//span[@class="product-sku__value"]/text()').extract_first()
                image_url = response.xpath('//*[@id="image-main"]/@src').extract_first()
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('identifier', identifier+'_'+o_id)
                loader.add_value('sku', sku)
                loader.add_value('category', category)
                loader.add_value('url', response.url)
                loader.add_value('image_url', response.urljoin(image_url))
                loader.add_value('price', price)
                option_item = loader.load_item()
                yield option_item
