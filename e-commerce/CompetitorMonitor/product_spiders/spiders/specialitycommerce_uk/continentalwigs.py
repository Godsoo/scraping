import os
import re
import json
import itertools
import demjson

from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ContinentalWigsSpider(BaseSpider):
    name = 'specialitycommerceuk-continentalwigs.co.uk'
    allowed_domains = ['continentalwigs.co.uk']

    start_urls = ['http://www.continentalwigs.co.uk/']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="block_top_menu"]/ul/li/a/@href').extract()		
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_products)    

    def parse_products(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_cats = hxs.select('//a[@class="subcategory-name"]/@href').extract()
        for sub_cat in sub_cats:
            yield Request(urljoin_rfc(base_url, sub_cat), callback=self.parse_products)

        products = hxs.select('//a[@class="product-name"]/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        next = hxs.select('//a[contains(b/text(), "Next")]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_products)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        brand = ''

        product_name = hxs.select('//h1[@itemprop="name"]/text()').extract()
        product_name = product_name[0].strip()
       
        product_price = hxs.select('//span[@itemprop="price"]/text()').extract()
        product_price = extract_price(product_price[0]) if product_price else 0
       
        product_code = response.xpath('//input[@name="id_product"]/@value').extract()[0]

        image_url = hxs.select('//span/img[@itemprop="image"]/@src').extract()
        image_url = image_url[0] if image_url else ''
        
        categories = hxs.select('//span[@class="navigation_page"]/span/a/span/text()').extract()
        categories = categories[1:] if categories else ''
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('shipping_cost', 5)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', product_code)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url))
        loader.add_value('category', categories)
        loader.add_value('price', product_price)
        if loader.get_output_value('price')==0:
            loader.add_value('stock', 0)

        item = loader.load_item()
        try:
            body = ' '.join(response.body.split('\n'))
            options = body.split('ekmProductVariantData[0] = ')[-1].split('</script>')[0].strip()
            options = demjson.decode(options)
        except:
            options = None


        main_options = []

        options = hxs.select('//ul[@id="color_to_pick_list"]/li')
        if options:
            for option in options:
                option_name = option.select('a/@title').extract()[0]
                option_identifier = option.select('a/@id').re('_(.*)')[0]
                main_options.append((option_identifier, option_name))

        more_options = []
        style_options = response.xpath('//div[@class="attribute_list"]//li[div[@class="radio"]]')
        if style_options:
            for option in style_options:
                option_name = option.xpath('span/text()').extract()[0]
                option_identifier = option.xpath('..//input/@value').extract()[0]
                more_options.append((option_identifier, option_name))

        group_options = []
        options_containers = hxs.select('//select[contains(@name, "group_")]')
        if options_containers:
            for options_container in options_containers:
                element_options = []
                for option in options_containers.select('option[@value!=""]'):
                    option_id = option.select('@value').extract()[0]
                    option_name = option.select('text()').extract()[0]
                    option_attr = (option_id, option_name)
                    element_options.append(option_attr)
                group_options.append(element_options)

        options = []
        combined_options = []

        if main_options:
            combined_options.append(main_options)

        if more_options:
            combined_options.append(more_options)

        if group_options:
            combined_options += group_options

        if combined_options:
            combined_options = list(itertools.product(*combined_options))
            for combined_option in combined_options:
                final_option = {}
                for option in combined_option:
                    final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                    final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                options.append(final_option)
        #else:
        #    for main_option in main_options:
        #        final_option = {}
        #        final_option['desc'] = ' ' + main_option[1]
        #        final_option['identifier'] = '-' + main_option[0]
        #        options.append(final_option)

        if options:
            for option in options:
                item_option = deepcopy(item)
                item_option['identifier'] = item_option['identifier'] + option['identifier']
                item_option['name'] = item_option['name'] + option['desc']
                item_option['sku'] = item_option['identifier']
                #item_option['price'] = option_price
                yield item_option
        else:
            options = hxs.select('//select[@class="ekm-productoptions-dropdown-option"]/option')
            if options:
                for option in options:
                    item_option = deepcopy(item)
                    item_option['identifier'] = item_option['identifier'] + '-' + option.select('@value').extract()[0]
                    item_option['name'] = item_option['name'] + ' ' + option.select('text()').extract()[0]
                    item_option['sku'] = item_option['identifier']
                    yield item_option
            else:
                yield item
