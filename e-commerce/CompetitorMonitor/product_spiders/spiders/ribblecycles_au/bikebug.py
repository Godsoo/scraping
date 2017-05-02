# -*- coding: utf-8 -*-
import re
import json
from decimal import Decimal
from copy import deepcopy


from scrapy.spider import BaseSpider

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price

from scrapy import log

from scrapy.utils.url import add_or_replace_parameter


class Bikebug(BaseSpider):
    name = 'ribblecycles_au-bikebug.com'
    allowed_domains = ['bikebug.com']
    start_urls = ('http://www.bikebug.com',)

    def parse(self, response):
        formdata = {'country_id': '13', 'currency': 'AUD'}

        yield FormRequest('http://www.bikebug.com',
                          formdata=formdata,
                          callback=self.parse_currency,
                          dont_filter=True)

    def parse_currency(self, response):
        yield Request('http://www.bikebug.com', callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)

        categories = response.xpath('//table[@class="Left_infoBoxContents"]//td[@class="Left_category"]/a/@href').extract()
        for category in categories:
            yield Request(response.urljoin(category), callback=self.parse_products)

        products = response.xpath('//h2[@class="product-name"]/a/@href').extract()
        for url in products:
            yield Request(response.urljoin(url), callback=self.parse_product)

        next_page = response.xpath('//a[contains(@title, "Next Page")]/@href').extract()
        if next_page:
            yield Request(response.urljoin(next_page[0]), callback=self.parse_products)

    def parse_product(self, response):
        base_url = get_base_url(response)

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        name = ''.join(response.xpath('//h1[@class="PrpdocutName"]//text()').extract()).strip()
        product_loader.add_value('name', name)
        brand = response.xpath('//span[@class="parent_product_manufacture_logo"]/img/@alt').extract()
        brand = brand[0].strip() if brand else ''
        product_loader.add_value('brand', brand)
        identifier = response.xpath('//input[@name="products_id"]/@value').extract()
        if not identifier:
            identifier = re.findall('custom_product_id=(\d+)', response.body)
        product_loader.add_value('identifier', identifier[0])
        product_loader.add_value('sku', identifier[0])
        category = response.xpath('//div[@class="breadcrumb"]//span[@itemprop="title"]/text()').extract()[1:-1]
        product_loader.add_value('category', category)

        image_url = response.xpath('//span[@class="image_container"]/img/@src').extract()
        if image_url:
            image_url = response.urljoin(image_url[0])
            product_loader.add_value('image_url', image_url)

        product = product_loader.load_item()

        options = response.xpath('//table[@id="product_price_list"]//tr[not(contains(@class, "HeadingRow"))]')
        if options:
            for option in options:
                prod = Product(product)
                product_loader = ProductLoader(item=prod, response=response)
                option_name = option.xpath('td/div[@class="subproduct_name"]/text()').extract()
                if option_name:
                    option_name = name + ' ' + option_name[0].strip()
                    product_loader.add_value('name', option_name)
                identifier = option.xpath('.//input[@name="sub_products_id[]"]/@value').extract()
                if not identifier:
                    identifier = option.xpath('.//input[@name="email_me_products_id"]/@value').extract()
                if not identifier:
                    identifier = option.xpath('.//input[@name="products_id"]/@value').extract()

                if identifier:
                    product_loader.add_value('identifier', product['identifier'] + '-' + identifier[0])
                else:
                    log.msg(' >>>>>> Possible wrong identifier: ' + response.url)

                sku = product_loader.get_output_value('identifier')
                product_loader.add_value('sku', sku)
                price = option.xpath('.//span[@class="productSpecialPrice"]/text()').extract()
                if not price:
                    price = option.xpath('.//span[@class="listing-price"]/text()').extract()
                price = price[0] if price else 0
                product_loader.add_value('price', price)
                in_stock = option.xpath('.//span[@class="instock" and text()="In Stock"]').extract()
                if not in_stock or not product_loader.get_output_value('price'):
                    product_loader.add_value('stock', 0)
                if product_loader.get_output_value('price') < 70:
                    product_loader.add_value('shipping_cost', Decimal('9.90'))
                yield product_loader.load_item()
        else:
            log.msg(' >>>>> ERROR: NO OPTIONS' + response.url)
            #if product['price'] < 70:
            #    product['shipping_cost'] = Decimal('9.90')
            '''
            selectors = response.xpath('//select[@class="build_attributeset_selector"]')
            options = selectors[0].xpath('option/@value').extract()
            for option in options:
                custom_product_id = re.findall('custom_product_id=(\d+)', response.body)[0]
                formdata = {'build_attributeset_id': selectors[0].xpath('@id').extract()[0],
                            'custom_product_id': custom_product_id,
                            'products_id': option}
                url = 'http://www.bikebug.com/product_information_loader.php'
                yield FormRequest(url, formdata=formdata, callback=self.parse_selector,
                                  meta={'selectors': selectors[1:],
                                        'custom_product_id': custom_product_id,
                                        'options_data': [],
                                        'product': deepcopy(product)})
            '''
            #yield product

    def parse_selector(self, response):
        data = json.loads(response.body)
        hxs = HtmlXPathSelector(text=data['variant'])

        product = response.meta['product']
        selectors = deepcopy(response.meta['selectors'])
        custom_product_id = response.meta['custom_product_id']
        if not selectors:
            options = hxs.select('//input[not(@value="0")]')
            for option in options:
                formdata = {'custom_product_id': custom_product_id}
                name = ''
                identifier = ''

                option_data = {'attribute': option.select('@name').extract()[0],
                               'value': option.select('@value').extract()[0],
                               'name': option.select('@data').extract()[0].strip()}

                options_data = response.meta['options_data']
                options_data.append(option_data)
                for option_data in options_data:
                    formdata[option_data['attribute']] = option_data['value']
                    name += ' ' + option_data['name']
                    identifier += '-' + option_data['value']
                url = 'http://www.bikebug.com/product_information_loader.php'
                yield FormRequest(url, dont_filter=True, callback=self.parse_final_option, formdata=formdata,
                                  meta={'name': name, 'identifier': identifier, 'product': deepcopy(product)})

        else:
            options = hxs.select('//input[not(@value="0")]')
            for option in options:
                sel_options = selectors[0].xpath('option[not(@value="0")]/@value').extract()
                for sel_option in sel_options:
                    options_data = deepcopy(response.meta['options_data'])

                    formdata = {'build_attributeset_id': selectors[0].xpath('@id').extract()[0],
                                'custom_product_id': custom_product_id,
                                'products_id': sel_option}

                    url = 'http://www.bikebug.com/product_information_loader.php'
                    option_data = {'attribute': option.select('@name').extract()[0],
                                   'value': option.select('@value').extract()[0],
                                   'name': option.select('@data').extract()[0].strip()}
                    options_data.append(option_data)
                    yield FormRequest(url, dont_filter=True, callback=self.parse_selector,
                                      formdata=formdata, meta={'selectors': selectors[1:],
                                                               'options_data': options_data,
                                                               'custom_product_id': custom_product_id,
                                                               'product': deepcopy(product)})

    def parse_final_option(self, response):
        product = response.meta['product']
        name = response.meta['name']
        identifier = response.meta['identifier']

        product['name'] += name
        product['identifier'] += identifier
        product['sku'] = product['identifier']
        product['price'] = 0
        yield product
