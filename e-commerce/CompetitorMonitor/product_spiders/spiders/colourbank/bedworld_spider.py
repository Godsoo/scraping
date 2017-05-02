# -*- coding: utf-8 -*-
import re
import json
import itertools
from decimal import Decimal

from scrapy import Spider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price


def normalize_space(s):
    """ Cleans up space/newline characters """
    return re.sub(r'\s+', ' ', s.replace(u'\xa0', ' ').strip())


class Meta(Item):
    net_price = Field()


class BedworldSpider(Spider):
    name = "colourbank-bedworld.net"
    allowed_domains = ['bedworld.net']
    start_urls = ['http://www.bedworld.net/catalog/seo_sitemap/product/']

    csv_file = 'bedworld.net_products.csv'

    def _start_requests(self):
        yield Request('http://www.bedworld.net/sweet-dreams-brisbane-fabric-ottoman-bed/', callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[@class="sitemap"]//a/@href').extract():
            yield Request(url, callback=self.parse_product)

        for url in hxs.select('//div[contains(@class, "pages")]//a/@href').extract():
            yield Request(url)

    def parse_list(self, response):
        base_url = get_base_url(response)

        for cat_url in response.xpath('//div[@class="nav-container"]/div//ul/li/a/@href').extract():
            yield Request(urljoin_rfc(base_url, cat_url), callback=self.parse_list)

        for url in response.xpath('//li[@class="item"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

        next = response.xpath('//a[contains(@class, "next")]/@href').extract()
        if next:
            yield Request(next[0], callback=self.parse_list)

    def parse_product(self, response):
        for url in response.xpath('//a[contains(@class,"size-boxes")]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

        product_name = response.xpath('//h1[@itemprop="name"]/text()').extract()[0]

        product_image = response.xpath('//a[@id="zoom-btn"]/@href').extract()
        if product_image:
            product_image = urljoin_rfc(get_base_url(response), product_image[0])

        product_brand = response.xpath("//table[@id='product-attribute-specs-table']/tbody/"
                                       "tr[th[text()='Manufacturer']]/td/text()").extract()[0]
        product_brand = product_brand[0] if product_brand else ''

        product_config_reg = re.search('var spConfig = new Product.Config\((\{.*\})\);', response.body)
        product_identifier = response.xpath('//input[@name="product"]/@value').extract()[0]

        if product_config_reg:
            products = json.loads(product_config_reg.group(1))
            for identifier, product in products['childProducts'].items():
                product_loader = ProductLoader(item=Product(), response=response)
                if identifier:
                    product_loader.add_value('identifier', product_identifier + '-' + identifier)
                else:
                    product_loader.add_value('identifier', product_identifier)
                product_loader.add_value('price', product[u'finalPrice'])
                option_name = product_name
                for attr_id, attribute in products[u'attributes'].items():
                    for option in attribute['options']:
                        if identifier in option['products']:
                            option_name += ' ' + option['label']
                product_loader.add_value('name', re.sub(r' \((.+?)\)', r'', option_name))
                product_loader.add_value('url', response.url)
                product_loader.add_value('brand', product_brand)
                product_loader.add_value('image_url', product_image)

                if identifier:
                    yield Request('http://www.bedworld.net/oi/ajax/co/?id=' + identifier + '&pid=' + product_identifier,
                                  meta={'item': product_loader.load_item()},
                                  callback=self.parse_options)
                else:
                    price = product_loader.get_output_value('price')
                    net_price = price / Decimal('1.2')

                    p = product_loader.load_item()
                    meta_ = Meta()
                    meta_['net_price'] = str(net_price)
                    p['metadata'] = meta_

                    yield p
        else:
            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', re.sub(r' \((.+?)\)', r'', product_name))
            product_loader.add_value('brand', product_brand)
            product_loader.add_value('identifier', product_identifier)
            product_loader.add_value('url', response.url)
            product_loader.add_value('image_url', product_image)
            price = response.xpath('//span[@id="product-price-' + product_identifier + '"]//text()').re(r'([\d.,]+)')
            price = price[0] if price else 0
            product_loader.add_value('price', price)

            option_elements = []
            dropdown_elements = response.xpath('//select[contains(@class, "product-custom-options")]')
            for dropdown_options in dropdown_elements:
                options = []
                for dropdown_option in dropdown_options.select('option[@value!=""]'):
                    option = {}
                    option['identifier'] = dropdown_option.select('@value').extract()[0]
                    option['desc'] = dropdown_option.select('.//text()').extract()[0].split('+')[0]
                    option['price'] = dropdown_option.select('@price').extract()[0]
                    options.append(option)
                option_elements.append(options)

            final_options = []
            if option_elements:
                combined_options = list(itertools.product(*option_elements))
                for combined_option in combined_options:
                    final_option = {}
                    for option in combined_option:
                        final_option['desc'] = final_option.get('desc', '') + option['desc']
                        final_option['price'] = final_option.get('price', Decimal(0)) + extract_price(option['price'])
                        final_option['identifier'] = final_option.get('identifier', '') + '-' + option['identifier']
                    final_options.append(final_option)

            if final_options:
                for opt in final_options:
                    opt_product = product_loader.load_item()
                    opt_product['name'] += ' ' + normalize_space(opt['desc'])
                    opt_product['price'] += opt['price']
                    opt_product['identifier'] += opt['identifier']
                    price = Decimal(opt_product['price'])
                    net_price = price / Decimal('1.2')

                    meta_ = Meta()
                    meta_['net_price'] = str(net_price)
                    opt_product['metadata'] = meta_

                    yield opt_product
            else:
                price = product_loader.get_output_value('price')
                net_price = price / Decimal('1.2')

                p = product_loader.load_item()
                meta_ = Meta()
                meta_['net_price'] = str(net_price)
                p['metadata'] = meta_

                yield p

    def parse_options(self, response):
        options = response.xpath('//option[@value!=""]')
        if not options:
            product = response.meta['item']
            price = Decimal(product['price'])
            net_price = price / Decimal('1.2')

            meta_ = Meta()
            meta_['net_price'] = str(net_price)
            product['metadata'] = meta_

            yield product

        else:
            for opt in options:
                product = Product(response.meta['item'])
                product['name'] += ' ' + normalize_space(''.join(opt.select('./text()').extract()))
                product['price'] += extract_price(''.join(opt.select('./@price').extract()))
                product['identifier'] += '-' + ''.join(opt.select('./@value').extract())

                price = Decimal(product['price'])
                net_price = price / Decimal('1.2')

                meta_ = Meta()
                meta_['net_price'] = str(net_price)
                product['metadata'] = meta_

                yield product
