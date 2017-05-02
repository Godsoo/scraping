"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/5174

Extract all products including product options.
"""
import scrapy
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import re
import json


class ModadoorsSpider(scrapy.Spider):
    name = 'leaderstores-modadoors.co.uk'
    allowed_domains = ['modadoors.co.uk']
    start_urls = ('http://www.modadoors.co.uk/collections/all',)

    def parse(self, response):
        for url in response.xpath('//ul[@class="pagination-custom"]//a/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse)

        for url in response.xpath('//a[@class="product-grid-item"]/@href').extract():
            yield scrapy.Request(response.urljoin(url), callback=self.parse_product)

    def parse_product(self, response):
        variants = re.search(r'var meta = \{"product":(\{.*)\};', response.body)
        if variants:
            image_url = response.xpath('//img[@itemprop="image"]/@src').extract_first()
            product_data = json.loads(variants.groups()[0])
            identifier = product_data['id']
            brand = product_data.get('vendor', 'MODA Doors')
            category = product_data.get('type')
            for variant in product_data['variants']:
                name = variant['name']
                sub_id = variant['id']
                price = variant['price'] / 100.0
                sku = variant['sku']
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', name)
                loader.add_value('identifier', "{}_{}".format(identifier, sub_id))
                loader.add_value('sku', sku)
                loader.add_value('brand', brand)
                loader.add_value('category', category)
                loader.add_value('url', response.url)
                loader.add_value('image_url', response.urljoin(image_url))
                loader.add_value('price', price)
                if price == 0:
                    loader.add_value('stock', 0)
                option_item = loader.load_item()
                yield option_item
        else:
            self.log('Error: no variants! url:{}'.format(response.url))