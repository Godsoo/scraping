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

class MuscleFinesseSpider(BaseSpider):
    name = 'usn-musclefinesse.com'
    allowed_domains = ['musclefinesse.com', 'cdn-gae-premium.instantsearchplus.com']
    start_urls = ['http://www.musclefinesse.com/brands/usn.html']

    def start_requests(self):
        brands = {'USN': 'http://www.musclefinesse.com/brands/usn.html',
                  'Optimum Nutrition': 'http://www.musclefinesse.com/brands/optimum-nutrition.html',
                  'BSN': 'http://www.musclefinesse.com/brands/bsn.html',
                  'PhD': 'http://www.musclefinesse.com/brands/phd-nutrition.html',
                  'Maxi Nutrition': 'http://www.musclefinesse.com/brands/maxi-nutrition.html',
                  'Reflex': 'http://www.musclefinesse.com/brands/reflex-nutrition.html',
                  'Mutant': 'http://www.musclefinesse.com/brands/mutant.html',
                  'Cellucor': 'http://www.musclefinesse.com/brands/cellucor.html',
                  'Sci-MX': 'http://www.musclefinesse.com/brands/sci-mx.html'}

        for brand, url in brands.iteritems():
            yield Request(url, meta={'brand': brand})

        search_url = "http://cdn-gae-premium.instantsearchplus.com/full_text_search?q=%s&UUID=1a361b72-99ad-4a2d-a658-ca84191c2f12&p=1&store_id=1&cdn_cache_key=1440603070&facets_required=0&callback=ispSearchResult&related_search=1"

        for brand in brands.keys():
            url = search_url % brand
            yield Request(url, callback=self.parse_search, meta={'brand': brand})

    def parse_search(self, response):
        json_data = re.search("ispSearchResult\((.*)\);", response.body)
        brand = response.meta.get('brand', '')
        if json_data:
            items = json.loads(json_data.group(1))['items']
            for item in items:
                if brand.upper() in item.get('l', '').upper().strip():
                    yield Request(item['u'], callback=self.parse_product, meta=response.meta)
            if items:
                current_page = int(url_query_parameter(response.url, 'p', 0))
                next_url = add_or_replace_parameter(response.url, 'p', str(current_page + 1))
                yield Request(next_url, callback=self.parse_search, meta=response.meta)
       

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = response.css('.item').xpath('.//h2/a/@href').extract()
        for product in products:
            yield Request(product, callback=self.parse_product, meta=response.meta)

        next_page = hxs.select('//a[@class="next" and @href!="#"]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, callback=self.parse, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        brand = response.meta.get('brand', '')

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@id="productname"]/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', brand)
        #categories = hxs.select('//ul[@class="breadcrumbs"]//a/text()').extract()[0:-1]
        loader.add_value('category', response.meta.get('brand', ''))

        identifier = response.xpath('//input[@name="product"]/@value').extract()
        if not identifier:
            log.msg('PRODUCT WHIOUT IDENTIFIER: ' + response.url)
            return

        loader.add_value('sku', identifier[0])
        loader.add_value('identifier', identifier[0])
        image_url = response.css('.main-image img::attr(src)').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])

        price = response.xpath('//span[@id="product-price-'+identifier[0]+'" and @class="price"]/text()').extract()
        if not price:
            price = response.xpath('//span[@id="product-price-'+identifier[0]+'"]/span[@class="price"]/text()').extract()

        if not price:
            price =  hxs.select('//div[@id="product_price"]//span[@class="price"]/text()').extract()

        loader.add_value('price', price[-1])

        in_stock =  response.xpath('//p[@class="availability in-stock"]')
        if not in_stock:
            loader.add_value('stock', '0')

        if loader.get_output_value('price') <= 49.99:
            loader.add_value('shipping_cost', 2.95)

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

                if option_item['price'] <= 49.99:
                    option_item['shipping_cost'] = 2.95

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
                    #option_item['price'] += prices[option_identifier]
                    if not option_item['price']:
                        option_item['stock'] = 0

                    if option_item['price'] <= 49.99:
                        option_item['shipping_cost'] = 2.95

                    yield option_item
                    
            else:
                yield item
