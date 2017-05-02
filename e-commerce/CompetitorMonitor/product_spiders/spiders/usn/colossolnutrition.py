import os
import json
import re
from copy import deepcopy
from decimal import Decimal

from scrapy import log

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from utils import extract_price


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class ColossolNutritionSpider(BaseSpider):
    name = 'usn-colossolnutrition.com'
    allowed_domains = ['colossolnutrition.com']
    start_urls = ['http://www.colossolnutrition.com']

    def start_requests(self):
        brands = {'Optimum Nutrition': ['http://www.colossolnutrition.com/categories/manufacturer/39-optimum-nutrition'], 
                  'BSN': ['http://www.colossolnutrition.com/bsn-supplements'], 
                  'PhD': ['http://www.colossolnutrition.com/categories/manufacturer/49-phd-nutrition'],
                  'Maxi Nutrition': ['http://www.colossolnutrition.com/categories/manufacturer/43-maxi-nutrition'], 
                  'Reflex': ['http://www.colossolnutrition.com/categories/manufacturer/41-reflex'],
                  'Mutant': ['http://www.colossolnutrition.com/categories/manufacturer/52-mutant'],
                  'Cellucor': ['http://www.colossolnutrition.com/categories/cellucor'],
                  'USN': ['http://www.colossolnutrition.com/usn']}
        for brand, brand_urls in brands.items():
            for brand_url in brand_urls:
                yield Request(brand_url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="name"]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        next_page = hxs.select('//div[@class="pagination"]//a[@class="next"]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, callback=self.parse, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@class="pro-name"]/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand'))
        categories = hxs.select('//div[contains(@class,"breadcrumbs")]/a/text()').extract()
        for category in categories[2:]:
            loader.add_value('category', category)

        identifier = hxs.select('.//input[@type="hidden" and @name="product_id"]/@value')[0].extract()
        loader.add_value('identifier', identifier)
        # sku = hxs.select('').extract()
        # loader.add_value('sku', sku)

        image_url = hxs.select('//div[@class="image"]/a/@href').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

        loader.add_value('shipping_cost', '0.00')

        price = hxs.select('//div[@class="total-price"]/span[@class="price-total"]/text()').extract()
        loader.add_value('price', price)

        self.log(loader.get_output_value('price'))
        if Decimal(loader.get_output_value('price')) < Decimal('30.00'):
            loader.add_value('shipping_cost', '2.99')

        stock = hxs.select('.//div[@class="stock-level"]/span[contains(text(),"In Stock")]')
        if not stock:
            loader.add_value('stock', 0)

        item = loader.load_item()
        options = hxs.select('//div[@class="options"]/div/select/option[not(contains(text(),"Select"))]')
        for option in options:
            option_name = option.select('./text()')[0].extract().strip()
            option_item = deepcopy(item)
            option_item['identifier'] = '{}-{}'.format(identifier, option.select('./@value')[0].extract())
            option_item['name'] += ' ' + option_name
            yield option_item
        else:
            yield item