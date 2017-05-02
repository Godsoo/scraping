import os
import re
import json
import itertools

from scrapy.spider import BaseSpider
from scrapy.item import Item, Field
from scrapy.http import Request
from scrapy.utils.url import add_or_replace_parameter, url_query_parameter

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader


HERE = os.path.abspath(os.path.dirname(__file__))


class ColemanfurnitureSpider(BaseSpider):
    name = '1stopbedrooms-colemanfurniture.com'
    allowed_domains = ['colemanfurniture.com', 'colemanfurniture.ecomm-nav.com']

    start_urls = ['http://colemanfurniture.com/']
    start_urls = ['http://colemanfurniture.com/decor/rugs.htm']

    def parse(self, response):
        categories = response.xpath('//div[contains(@class, "div-category")]//a/@href').extract()
        categories += response.xpath('//ul[contains(@class, "category-list")]//a/@href').extract()
        for category in categories:
            yield Request(category)

        brands = response.xpath('//dl[@id="narrow-by-list"]//a[contains(@href, "?manufacturer=")]/@href').extract()
        if response.meta.get('extract_brands', True):
            for brand in brands:
                manufacturer_id = url_query_parameter(brand, 'manufacturer', None)
                if manufacturer_id:
                    manufacturer_id = manufacturer_id.split(',')[0]
                    if brand.endswith(manufacturer_id):
                        yield Request(brand, meta={'extract_brands': False})

        products = response.xpath('//h3[contains(@class, "product-name")]/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)

        next = response.xpath('//a[contains(text(), "Next")]/@href').extract()
        if next:
            yield Request(next[0])

    def parse_product(self, response):
        extra_products = response.xpath('//div[contains(@class, "product-cross")]//div[contains(@class, "related-title")'']/a[not(contains(@href, "JavaScript"))]/@href').extract()
        for extra_product in extra_products:
            yield Request(extra_product, callback=self.parse_product, meta=response.meta)

        brand = response.xpath('//div[span[contains(text(), "Brands")]]/span[@class="spc-data"]/text()').extract()
        brand = brand[0].strip() if brand else ''

        name = response.xpath('//h1[@class="detail-heading pull-left"]/text()').extract()[0].strip()
        image_url = response.xpath('//img[@id="image"]/@src').extract()[0]
        identifier = response.xpath('//input[@name="product"]/@value').extract()[0]
        sku = response.xpath('//div[@id="product_id"]/span/text()').extract()[0]
        price = response.xpath('//meta[@property="bt:price"]/@content').extract()[0]
        price = extract_price(price)

        options_bundle = re.search(r'new Product.Bundle\((.*)\)', response.body)
        if options_bundle:
            self.log('OPTION BUNDLE: ' + response.url)
            combined_options = []
            product_data = json.loads(options_bundle.groups()[0])

            selected = map(lambda x: x[0], product_data['selected'].values())

            # Calculate base price, summarizing all the prices for products without options
            base_price = 0
            for id, options in product_data['options'].iteritems():
                if options['title'].lower().strip() != 'set includes':
                    continue
                if len(options['selections'].values()) < 2:
                    for option_id, option in options['selections'].iteritems():
                        base_price += extract_price(str(option['priceInclTax']))

            for id, options in product_data['options'].iteritems():
                if options['title'].lower().strip() != 'set includes':
                    continue
                element_options = []
                # Extract options only for products with option selector
                if len(options['selections'].values()) > 1:
                    for option_id, option in options['selections'].iteritems():
                        if option_id in selected:
                            continue
                        option_id = option_id
                        option_name = option['name']
                        option_price = extract_price(str(option['priceInclTax']))
                        option_attr = (option_id, option_name, option_price)
                        element_options.append(option_attr)
                    combined_options.append(element_options)

            if combined_options:
                combined_options = list(itertools.product(*combined_options))
                options = []
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                        final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                        final_option['price'] = final_option.get('price', 0) + option[2]
                    options.append(final_option)

                for option in options:
                    loader = ProductLoader(response=response, item=Product())
                    loader.add_value('identifier', identifier + option['identifier'])
                    loader.add_value('sku', sku)
                    loader.add_value('brand', brand)
                    loader.add_value('category', brand)
                    loader.add_value('url', response.url)
                    loader.add_value('image_url', image_url)
                    loader.add_value('name', name + ' ' + option['desc'].strip())
                    loader.add_value('price', base_price + option['price'])
                    yield loader.load_item()
            else:
                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', identifier)
                loader.add_value('sku', sku)
                loader.add_value('brand', brand)
                loader.add_value('category', brand)
                loader.add_value('url', response.url)
                loader.add_value('image_url', image_url)
                loader.add_value('category', brand)
                loader.add_value('name', name)
                loader.add_value('price', price)
                yield loader.load_item()
        else:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', identifier)
            loader.add_value('sku', sku)
            loader.add_value('brand', brand)
            loader.add_value('category', brand)
            loader.add_value('url', response.url)
            loader.add_value('image_url', image_url)
            loader.add_value('category', brand)
            loader.add_value('name', name)
            loader.add_value('price', price)
            yield loader.load_item()

            # Extract price in set as a separate product
            headers = response.xpath(
                '//div[@class="buy-in-set-price-grid"]/div[contains(@class, "header")]/div/text()').extract()
            prices = response.xpath(
                '//div[@class="buy-in-set-price-grid"]/div[contains(@class, "price")]/div/text()').extract()
            try:
                set_price_index = headers.index('Price in a set')
            except ValueError:
                set_price_index = -1
            if set_price_index >= 0:
                price = extract_price(prices[set_price_index])

                loader = ProductLoader(response=response, item=Product())
                loader.add_value('identifier', 'set-' + identifier)
                loader.add_value('sku', 'SET ' + sku)
                loader.add_value('brand', brand)
                loader.add_value('category', brand)
                loader.add_value('url', response.url)
                loader.add_value('image_url', image_url)
                loader.add_value('category', brand)
                loader.add_value('name', name)
                loader.add_value('price', price)
                yield loader.load_item()