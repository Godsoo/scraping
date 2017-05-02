import os
import json
import re
import itertools
from copy import deepcopy

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter, url_query_parameter
from scrapy.utils.response import get_base_url

from utils import extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class EchoSupplementsSpider(BaseSpider):
    name = 'reflexnutrition-echosupplements.com'
    allowed_domains = ['echosupplements.com', 'cdn-gae-premium.instantsearchplus.com']
    start_urls = ['http://www.echosupplements.com']

    def start_requests(self):
        brands = {'USN': 'http://www.echosupplements.com/brands/usn',
                  'Optimum Nutrition': 'http://www.echosupplements.com/brands/optimum-nutrition',
                  'PhD': 'http://www.echosupplements.com/brands/phd-nutrition',
                  'Reflex': 'http://www.echosupplements.com/brands/reflex-nutrition',
                  'Sci-MX': 'http://www.echosupplements.com/brands/sci-mx'}

        for brand, url in brands.iteritems():
            yield Request(url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//h3[@class="product__name"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        next = hxs.select('//a[@class="next i-next"]/@href').extract()
        if next:
            next = urljoin_rfc(get_base_url(response), next[0])
            yield Request(next, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        brand = response.meta.get('brand', '')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', brand)
        loader.add_value('category', brand)

        identifier = hxs.select('//input[@name="product"]/@value').extract()
        if not identifier:
            log.msg('PRODUCT WHIOUT IDENTIFIER: ' + response.url)
            return

        loader.add_value('sku', identifier[0])
        loader.add_value('identifier', identifier[0])
        image_url = hxs.select('//div[contains(@class, "product-image")]//img/@src').extract()
        if not image_url:
            image_url = hxs.select('//p[contains(@class, "product-image")]//img/@src').extract()

        if image_url:
            loader.add_value('image_url', image_url[0])

        price = hxs.select('//span[@id="product-price-'+identifier[0]+'" and @class="price"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="product-price-'+identifier[0]+'"]/span[@class="price"]/text()').extract()

        if not price:
            price =  hxs.select('//div[@id="product_price"]//span[@class="price"]/text()').extract()

        loader.add_value('price', price[-1])

        item = loader.load_item()


        options_config = re.search(r'var spConfig = new Product.Config\((.*)\)', response.body)
        if options_config:
            product_data = json.loads(options_config.groups()[0])
            products = {}
            prices = {}
            for attr in product_data['attributes'].itervalues():
                for option in attr['options']:
                    for product in option['products']:
                        products[product] = ' - '.join((products.get(product, ''), option['label']))
                        prices[product] = prices.get(product, 0) +  extract_price(option['price'])

            for option_identifier, option_name in products.iteritems():
                option_item = deepcopy(item)

                option_item['identifier'] += '-' + option_identifier
                option_item['name'] += option_name
                option_item['price'] += prices[option_identifier]
                if not option_item['price']:
                    option_item['stock'] = 0

                yield option_item
        else:
            options_bundle = re.search(r'new Product.Bundle\((.*)\)', response.body)
            if options_bundle:
                log.msg('OPTION BUNDLE: ' + response.url)
                combined_options = []
                product_data = json.loads(options_bundle.groups()[0])
                for id, options in product_data['options'].iteritems():
                    element_options = []
                    for option_id, option in options['selections'].iteritems():
                        option_id = option_id
                        option_name = option['name']
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
                    option_item = deepcopy(item)

                    option_item['identifier'] += option['identifier']
                    option_item['name'] += option['desc']
                    if not option_item['price']:
                        option_item['stock'] = 0

                    yield option_item
                    
            else:
                yield item
