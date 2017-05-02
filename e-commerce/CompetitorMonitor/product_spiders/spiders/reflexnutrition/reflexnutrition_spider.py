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

class ReflexNutritionSpider(BaseSpider):
    name = 'reflexnutrition-reflex-nutrition.com'
    allowed_domains = ['reflex-nutrition.com']
    start_urls = ['https://www.reflex-nutrition.com/shop/high-protein/instant-whey-pro-with-whey-protein-isolate',
                  'https://www.reflex-nutrition.com/shop/muscle-strength/one-stop-extreme-best-all-in-one-bodybuilding-supplement',
                  'https://www.reflex-nutrition.com/shop/weight-management/diet-whey-protein-shake-with-right-dose-of-cla',
                  'https://www.reflex-nutrition.com/shop/muscle-strength/instant-mass-heavyweight-our-best-weight-gainer-for-the-hardgainer']


    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        brand = response.meta.get('brand', '')

        loader = ProductLoader(item=Product(), response=response)
        name = ''.join(hxs.select('//h1[@itemprop="name"]//text()').extract())
        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('brand', 'Reflex Nutrition')
        categories = hxs.select('//ol[@class="breadcrumb"]/li/a/text()').extract()[2:]
        loader.add_value('category', categories)

        identifier = hxs.select('//input[@name="product_id"]/@value').extract()
        if not identifier:
            log.msg('PRODUCT WHIOUT IDENTIFIER: ' + response.url)
            return

        loader.add_value('sku', identifier[0])
        loader.add_value('identifier', identifier[0])
        image_url = hxs.select('//li/figure/img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[-1])

        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')


        item = loader.load_item()


        options = hxs.select('//form[@class="variations_form cart"]/@data-product_variations').extract()
        if options:
            options = json.loads(options[0])
            collected_options = []
            for option in options:
                weight = option['attributes'].get('attribute_weight')
                if not weight:
                    yield item
                    continue
                if weight not in collected_options:
                    collected_options.append(weight)
                    option_item = deepcopy(item)
                    option_item['identifier'] += '-' + weight
                    option_item['name'] += ' ' + weight
                    option_item['price'] = option['display_regular_price']
                    yield option_item
                
        else:
            yield item             
