'''
Ticket link: https://app.assembla.com/spaces/competitormonitor/tickets/5519
'''

import os
import csv
from w3lib.url import add_or_replace_parameter, url_query_parameter
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader, ProductLoaderWithoutSpacesEU as ProductLoaderEU
from product_spiders.lib.schema import SpiderSchema
from decimal import Decimal
from product_spiders.config import DATA_DIR


class PCComponentes(CrawlSpider):
    name = 'sonae-pccomponentes'
    allowed_domains = ['pccomponentes.pt']
    start_urls = ['https://www.pccomponentes.pt/']
    
    categories = LinkExtractor(restrict_xpaths=('//*[contains(@class, "menu-principal")]', '//*[contains(@class, "enlaces-clave")]'))
    
    rules = (Rule(categories, callback='parse_category'),)

    def start_requests(self):
        for url in self.start_urls:
            yield Request(url)

        if hasattr(self, 'prev_crawl_id'):
            filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)
            
            with open(filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    product = Product()
                    for key in row:
                        if row[key]:
                            product[key] = row[key].decode('utf8')
                    yield Request(row['url'],
                                  self.parse_product,
                                  meta={'item': Product(product)})
                    
    def parse_category(self, response):
        try:
            data = SpiderSchema(response).get_products()
        except:
            return
        products = False
        for product in data:
            if not product.get('sku'):
                continue
            products = True
            loader = ProductLoader(Product(), response=response)
            loader.add_value('identifier', product['sku'])
            loader.add_value('url', product['url'][0])
            loader.add_value('name', product['name'])
            loader.add_value('sku', product['sku'])
            category = response.css('a.GTM-breadcumb::text').extract()[1:] or response.meta.get('category')
            loader.add_value('category', category)
            loader.add_value('image_url', product['image'])
            loader.add_value('brand', product['brand'])
            if product['offers']['properties']['availability'] != 'in stock':
                loader.add_value('stock', 0)
            price = product['offers']['properties']['price']
            yield Request(loader.get_output_value('url'),
                    self.parse_product,
                    meta={'item': Product(loader.load_item())})
        if not products:
            return
        
        page = url_query_parameter(response.url, 'page')
        if page:
            url = add_or_replace_parameter(response.url, 'page', int(page)+1)
        else:
            id_families = response.xpath('//input[@data-key="idFamilies"]/@value').extract_first()
            if id_families:
                url = add_or_replace_parameter('https://www.pccomponentes.pt/listado/ajax?page=0&order=price-desc', 'idFamilies[]', id_families)
            elif response.url.endswith('/novedades/'):
                return
            elif response.url.endswith('/'):
                url = response.url + 'ajax?page=0&order=price-desc'
            else:
                return
            
        yield Request(url, self.parse_category, meta={'category': category})

    def parse_product(self, response):
        item = response.meta['item']
        data = SpiderSchema(response).get_product()
        category = response.css('a.GTM-breadcumb::text').extract()[1:]
        loader = ProductLoaderEU(Product(), response=response)
        loader.add_value(None, item)
        loader.replace_value('price', data['offers']['properties']['price'])
        loader.replace_value('category', category)
        if data['offers']['properties']['availability'] != 'inStock':
            loader.replace_value('stock', 0)
        yield loader.load_item()