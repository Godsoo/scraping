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

class TheSupplementStoreSpider(BaseSpider):
    name = 'usn-thesupplementstore.co.uk'
    allowed_domains = ['thesupplementstore.co.uk']
    start_urls = ['http://www.thesupplementstore.co.uk']

    def start_requests(self):
        brands = {'Sci-MX': ['https://www.thesupplementstore.co.uk/brands/sci_mx_nutrition'], 
                  'Optimum Nutrition': ['https://www.thesupplementstore.co.uk/brands/optimum_nutrition'], 
                  'BSN': ['https://www.thesupplementstore.co.uk/brands/bsn'], 
                  'PHD': ['https://www.thesupplementstore.co.uk/brands/phd_nutrition', 'https://www.thesupplementstore.co.uk/brands/phd_woman'],
                  'Maxi Nutrition': ['https://www.thesupplementstore.co.uk/brands/maxinutrition'], 
                  'Reflex': ['https://www.thesupplementstore.co.uk/brands/reflex_nutrition'],
                  'Mutant': ['https://www.thesupplementstore.co.uk/brands/mutant'],
                  'Cellucor': ['https://www.thesupplementstore.co.uk/brands/cellucor'],
                  'USN': ['https://www.thesupplementstore.co.uk/brands/usn', 'https://www.thesupplementstore.co.uk/brands/usn_endurance']}
        for brand, brand_urls in brands.items():
            for brand_url in brand_urls:
                yield Request(brand_url, meta={'brand': brand})

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        products = response.css('li.prod').xpath('div/h5/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(get_base_url(response), product), callback=self.parse_product, meta=response.meta)

        next_page = hxs.select('//link[@rel="next"]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page, callback=self.parse, meta=response.meta)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', response.meta.get('brand'))
        categories = hxs.select('//div[@id="breadcrumbs"]/div[@class="crumbs"]/span/a/span/text()').extract()
        for category in categories[2:]:
            loader.add_value('category', category)

        sku = hxs.select('//meta[@itemprop="sku"]/@content').extract()
        loader.add_value('sku', sku)

        image_url = hxs.select('//div[@id="product-image"]//img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))

        identifier = loader.get_output_value('name')

        loader.add_value('shipping_cost', '0.00')

        item = loader.load_item()

        variants = response.xpath('//div[@class="variant"]')
        if variants:
            for variant in variants:
                options = variant.select('.//tr')
                variant_name = variant.select('.//div[@class="title"]/h4/text()')[0].extract().strip()
                for option in options:
                    option_name = option.select('.//td[@class="name"]/text()')[0].extract().strip().encode('latin-1')
                    option_item = deepcopy(item)
                    option_item['identifier'] = '{}-{}-{}'.format(identifier, variant_name, option_name).decode('latin-1')
                    option_item['name'] += ' {} {}'.format(variant_name, option_name if option_name.lower() != variant_name.lower() else '').decode('latin-1')
                    option_item['name'] = option_item['name'].strip()
                    price = variant.xpath('.//span[@class="now"]/text()').extract_first() or variant.css('p.price span::text').extract_first()
                    option_item['price'] = extract_price(price) if price else Decimal('0.00')
                    if Decimal(option_item['price']) < Decimal('30.00'):
                        option_item['shipping_cost'] = '1.99'
                    stock = option.select('.//td[@class="stock instock"]')
                    if not stock:
                        option_item['stock'] = 0
                    option_item['image_url'] = variant.select('.//img/@src')[0].extract()
                    yield option_item
        else:
            self.log('PRODUCT WITHOUT OPTIONS: ' + response.url)