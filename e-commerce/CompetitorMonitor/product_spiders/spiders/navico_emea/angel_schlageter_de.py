import os
import re
import json
import csv
import urlparse

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from navicoitems import NavicoMeta

from scrapy import log

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class AngelSchlageterSpider(BaseSpider):
    name = 'navico-angel_schlageter.de'
    allowed_domains = ['angel-schlageter.de']

    start_urls = ['http://www.angel-schlageter.de/Echolote-Navigation---495.html']

    angelschlageter_products = {}

    def __init__(self, *args, **kwargs):
        super(AngelSchlageterSpider, self).__init__(*args, **kwargs)
        self.brands = ('lowrance', 'b&g', 'simrad', 'garmin', 'raymarine', 'humminbird')

    def start_requests(self):

        with open(HERE+'/angelschlageter_products.csv') as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.angelschlageter_products[row['Code'].strip().upper()] = row['Screen Size']

        yield Request('http://www.angel-schlageter.de/Echolote-Navigation---495.html')

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        categories = hxs.select('//div[contains(@class, "subcat")]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        products = hxs.select('//div[@class="pl_right"]/h1/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        product_name = hxs.select('//div[@class="product_text_detail"]/h1/text()')[0].extract()
        product_price = hxs.select('//strong[@class="product_price_detail"]/text()')[0].extract()
        sku = hxs.select('//div[@class="product_model_detail"]/text()[normalize-space()]').extract()
        sku = sku[0] if len(sku) > 1 else ''
        product_code = re.search('--(.*)\.html', response.url).groups()[0]
        image_url = hxs.select('//div[@id="zoom_wrapper"]/a/img/@src').extract()
        category = hxs.select('//li[@class="activeCat"]/a/text()').extract()
        if len(category) > 1:
            category = category[1]
        elif len(category) == 1:
            category = category[0]
        else:
            category = ''
        brand = product_name.split(' ')[0]
        brand = brand if brand.lower() in self.brands else ''
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('name', product_name)
        loader.add_value('url', response.url)
        loader.add_value('sku', sku)
        loader.add_value('identifier', product_code)
        loader.add_value('brand', brand)
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
        loader.add_value('category', category)
        product_price = extract_price(product_price.replace('.', '').replace(',', '.'))
        loader.add_value('price', product_price)
        if not product_price:
            loader.add_value('stock', 0)
 
        product = loader.load_item()
        metadata = NavicoMeta()
        metadata['screen_size'] = self.angelschlageter_products.get(sku.strip().upper(), '')
        product['metadata'] = metadata

        yield product

        # options parsing
        options = hxs.select('//div[@class="product_options_detail"]/select/option/text()').extract()
        for option in enumerate(options):
            option_data = re.search('(.*) \+ +([\d\,\.]+) EUR', option[1])
            if not option_data:
                log.msg('Option without price')
                continue
            option_data = option_data.groups()
            option_name, option_price = option_data
            option_price = float(option_price.replace('.', '').replace(',', '.'))

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', u'{} {}'.format(product_name.strip(), option_name.strip()))
            loader.add_value('url', response.url)
            loader.add_value('sku', sku)
            loader.add_value('identifier', u'{}.{}'.format(product_code, str(option[0])))
            loader.add_value('brand', brand)
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            loader.add_value('category', category)
            loader.add_value('price', str(float(product_price) + option_price))
            if not product_price:
                loader.add_value('stock', 0)

            product = loader.load_item()
            metadata = NavicoMeta()
            metadata['screen_size'] = self.angelschlageter_products.get(sku.strip().upper(), '')
            product['metadata'] = metadata

            yield product

