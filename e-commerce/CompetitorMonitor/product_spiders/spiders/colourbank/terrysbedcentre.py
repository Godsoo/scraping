# -*- coding: utf-8 -*-
import itertools
from copy import deepcopy

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import HtmlResponse, Request, FormRequest
from scrapy.utils.response import get_base_url
from urlparse import urljoin
from decimal import Decimal
from product_spiders.utils import extract_price

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader



class TerrysBedCentre(BaseSpider):
    name = "colourbank-terrysbedcentre.com"
    allowed_domains = ["terrysbedcentre.com"]
    start_urls = ["http://www.terrysbedcentre.com"]


    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        category_urls = hxs.select('//ul[@id="menu"]//a/@href').extract()
        for url in category_urls:
            yield Request(urljoin(base_url, url))
 
        pagination = hxs.select('//span[@class="pagination"]/a/@href').extract()
        for page in pagination:
            yield Request(urljoin(base_url, page))
            
        product_urls = hxs.select('//div[@class="category_product"]/h3/a/@href').extract()
        for url in product_urls:
            yield Request(urljoin(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//div[@id="page_content"]/h2/text()').extract()
        identifier = hxs.select('//input[@name="add"]/@value').extract()
        if not identifier:
            identifier = response.url.split('product_id=')[-1]
        else:
            identifier = identifier[0]
        
        
        price = hxs.select('//div[@id="product_detail"]/h1/text()').extract()
        price = extract_price(price[0])

        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('identifier', identifier)
        loader.add_value('sku', identifier)
        image_url = hxs.select('//div[@class="image"]/a/img/@src').extract()
        image_url = urljoin(base_url, image_url[0]) if image_url else ''
        loader.add_value('image_url', image_url)
        categories = hxs.select('//div[@id="breadcrumb"]/ul/li/a/text()').extract()
        categories = categories[1:-1] if categories else ''
        loader.add_value('category', categories)
        loader.add_value('url', response.url)
        out_of_stock = hxs.select('//p[@class="buy_button"]/strong[contains(text(), "out of stock")]')
        if out_of_stock:
            loader.add_value('stock', 0)

        product = loader.load_item()

        options_containers = hxs.select('//select[contains(@name, "productOptions") and not(contains(@name, "productOptions[21]"))]')

        if options_containers:
            options = []
            if len(options_containers)>1:
                combined_options = []
                for options_container in options_containers:
                    element_options = []
                    for option in options_container.select('option[@value!=""]'):
                        option_id = option.select('@value').extract()[0]
                        option_name = option.select('text()').extract()[0].split('(+')[0].strip()
                        option_price = option.select('text()').re('\(\+(.*)\)')
                        option_price = extract_price(option_price[0]) if option_price else 0
                        option_attr = (option_id, option_name, option_price)
                        element_options.append(option_attr)
                    combined_options.append(element_options)
                combined_options = list(itertools.product(*combined_options))

                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + ' ' + option[1]
                        final_option['identifier'] = final_option.get('identifier', '') + '-' + option[0]
                        final_option['price'] = final_option.get('price', 0) + option[2]
                    options.append(final_option)
            else:
                for option in options_containers.select('option[@value!=""]'):
                    final_option = {}
                    final_option['desc'] = ' ' + option.select('text()').extract()[0].split('(+')[0].strip()
                    final_option['identifier'] = '-' + option.select('@value').extract()[0]
                    option_price = option.select('text()').re('\(\+(.*)\)')
                    final_option['price'] = extract_price(option_price[0]) if option_price else 0
                    options.append(final_option)

            for option in options:
                option_product = deepcopy(product)
                option_product['identifier'] = option_product['identifier'] + option['identifier']
                option_product['name'] = option_product['name'] + option['desc']
                option_product['price'] =  option_product['price'] + option['price']
                option_product['sku'] = option_product['identifier']
                yield option_product
        else:
            yield product

        
