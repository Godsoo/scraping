# -*- coding: utf-8 -*-
from scrapy.spiders import Spider
from utils import extract_price

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader


class RibblecyclesSpider(Spider):
    name = 'ribblecycles_au-ribblecycles.com'
    allowed_domains = ['ribblecycles.co.uk']
    start_urls = ['http://www.ribblecycles.co.uk/feeds/au_en_auGoogleShoppingen_AU.xml']

    def parse(self, response):
        
        response.selector.register_namespace("g", "http://base.google.com/ns/1.0")

        for item in response.xpath('//item'):
            image_url = item.xpath('g:image_link/text()').extract()
            image_url = image_url[0] if image_url else ''
            category = item.xpath('g:product_type/text()').extract()
            category = category[0].split('>')[1:] if category else ''
            brand = item.xpath('g:brand/text()').extract()
            identifier = item.xpath('g:id/text()').extract()
            name = item.xpath('title/text()').extract_first()
            if name:
                name = name.replace('...', '').strip()
            price = item.xpath('g:price/text()').extract()
            price = extract_price(price[0]) if price else 0
            url = item.xpath('link/text()').extract()[0]
            out_of_stock = item.xpath('g:availability/text()').extract()[0] == 'out of stock'
        
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('identifier', identifier)
            product_loader.add_value('sku', identifier)
            product_loader.add_value('name', name)
            product_loader.add_value('image_url', image_url)
            product_loader.add_value('price', price)
            product_loader.add_value('url', url)
            product_loader.add_value('brand', brand)
            product_loader.add_value('category', category)
            if out_of_stock:
                product_loader.add_value('stock', 0)
            product = product_loader.load_item()
        
            yield product
