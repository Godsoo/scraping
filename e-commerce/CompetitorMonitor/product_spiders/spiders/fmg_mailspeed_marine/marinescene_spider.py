import os
import re
import json
import csv
import urlparse
import itertools

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class MarinesceneSpider(BaseSpider):
    name = 'fmg_ mailspeed_marine-marinescene.co.uk'
    allowed_domains = ['marinescene.co.uk']

    start_urls = ['http://www.marinescene.co.uk/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        main_categories = hxs.select('//nav[@id="menu"]//a/@href').extract()
        for category in main_categories:
            yield Request(category)

        sub_categories = hxs.select('//div[@class="subCategoriesInner"]//div[@class="viewCategory"]/a/@href').extract() 
        for category in sub_categories:
            yield Request(category)

        products = hxs.select('//div[contains(@class, "productsDetails")]//a[@itemprop="url"]/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product)    

        next_pages = hxs.select('//div[@class="showing"]/a/@href').extract()
        for page in next_pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        brands = hxs.select('//select[contains(@class, "searchManufacturer")]/option/text()').extract()

        loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()[0]
        product_price = hxs.select('//input[@class="priceBox"]/@value').extract()[0]

        product_code = hxs.select('//input[@name="prod_id"]/@value').extract()[0]
        image_url = hxs.select('//img[@itemprop="image"]/@src').extract()
        product_brand = ''
        for brand in brands:
            if brand.upper() in product_name.upper():
                product_brand = brand

        sku = re.findall(u'ecomm_prodid: \'(.*)\'', response.body)
        sku = sku[0] if sku else ''

        categories = hxs.select('//h2[@class="breadcrumbs"]/span/a/span/text()').extract()[1:-1]
        
        product_price = extract_price(product_price)

        options = hxs.select('//select[@name="options"]/option')
        if options:
            for option in options:
                loader = ProductLoader(response=response, item=Product())
                option_identifier = option.select('@value').extract()[0]
                option_name = option.select('text()').re(r'(.*) \(')[0]
                option_price = option.select('text()').re(u'\(\xa3(.*)\)')
                option_price = option_price[0] if option_price else '0'
                loader.add_value("identifier", product_code + '-' + option_identifier)
                loader.add_value('name', product_name + ' ' + option_name)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                loader.add_value('price', extract_price(option_price))
                loader.add_value('url', response.url)
                loader.add_value('sku', sku)
                loader.add_value('brand', product_brand)
                for category in categories:
                    loader.add_value('category', category)
                product = loader.load_item()
                yield product
        else:
            options_containers = hxs.select('//select[@name="options[]"]')
            if options_containers:
                combined_options = []
                for options_container in options_containers:
                    element_options = []
                    for option in options_container.select('option'):
                        option_id = option.select('@value').extract()[0]
                        option_name = option.select('text()').extract()[0]
                        option_attr = (option_id, option_name)
                        element_options.append(option_attr)
                    combined_options.append(element_options)

                combined_options = list(itertools.product(*combined_options))
                options = []
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                        final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                    options.append(final_option)

                for option in options:
                    loader = ProductLoader(response=response, item=Product())
                    option_name = option['desc']
                    option_identifier = option['identifier']
                    loader.add_value("identifier", product_code + option_identifier)
                    loader.add_value('name', product_name + option_name)
                    if image_url:
                        loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                    loader.add_value('price', product_price)
                    loader.add_value('url', response.url)
                    loader.add_value('sku', sku)
                    loader.add_value('brand', product_brand)
                    for category in categories:
                        loader.add_value('category', category)
                    product = loader.load_item()
                    yield product
            else:
                loader = ProductLoader(item=Product(), response=response)
                loader.add_value('name', product_name)
                loader.add_value('url', response.url)
                loader.add_value('sku', sku)
                loader.add_value('identifier', product_code)
                loader.add_value('brand', product_brand)
                if image_url:
                    loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
                for category in categories:
                    loader.add_value('category', category)
                loader.add_value('price', product_price)
                yield loader.load_item()
