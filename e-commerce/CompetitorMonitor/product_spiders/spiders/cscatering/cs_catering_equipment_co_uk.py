import os
import csv
import cStringIO

import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import XmlXPathSelector
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from product_spiders.base_spiders.primary_spider import PrimarySpider

from scrapy import log

class CSCateringMeta(Item):
    cost_price = Field()


ignore_categories = set([
    'bar-supplies',
    'beverage-machines',
    'beverage-service',
    'buffet-display',
    'chef-clothing',
    'chefs-knives',
    'cleaning-chemicals',
    'cleaning-hardware',
    'clearance',
    'cloths-gloves',
    'cookware',
    'crockery',
    'cutlery',
    'Default',
    'disposables',
    'food-storage',
    'footwear',
    'furniture',
    'glassware',
    'hotel-lobby',
    'hotel-room-products',
    'lighting',
    'menus-boards',
    'pastry-baking',
    'safety-signs',
    'service-trays',
    'spares-accessories',
    'special-offers',
    'table-linen',
    'tables-sinks',
    'tabletop',
    'trolleys-and-shelving',
    'utensils',
    'waiting-clothing',
    ])

class CSCateringSpider(PrimarySpider):
    name = 'cs-catering-equipment.co.uk'
    allowed_domains = ['cs-catering-equipment.co.uk']
    start_urls = ('http://www.cs-catering-equipment.co.uk/price_checker.php',)

    download_timeout = 30 * 60

    _skus = None

    csv_file = 'cscatering_products.csv'
    json_file = 'cscatering_metadata.json'

    ignore_brands = ['FALCON', 'CRAVEN']

    def has_sku(self, sku):
        if self._skus is None:
            self._skus = set()
            with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'nisbets.csv')) as f:
                reader = csv.DictReader(cStringIO.StringIO(f.read()))
                for row in reader:
                    self._skus.add(row['sku'].lower())
        return sku.lower() in self._skus

    def parse(self, response):
        xxs = XmlXPathSelector(response)

        for productxs in xxs.select('//product[attribute_set/text()!="spares-accessories"]'):
            loader = ProductLoader(item=Product(), selector=productxs)
            loader.add_xpath('sku', './product_id/text()')
            loader.add_xpath('identifier', './product_id/text()')
            loader.add_xpath('price', './product_price/text()')
            loader.add_xpath('name', './product_name/text()')
            loader.add_xpath('url', './product_url/text()')
            loader.add_xpath('category', './attribute_set/text()')
            loader.add_xpath('brand', './manufacturer/text()')
            brand = loader.get_output_value('brand').strip().upper()

            if brand in self.ignore_brands:
                log.msg('Ignoring product %s because of brand %s' % (loader.get_output_value('identifier'), brand))
                continue

            loader.add_value('stock', '1')

            item = loader.load_item()
            item['identifier'] = item['identifier'].upper()

            cost_price = productxs.select('./cost/text()').extract()
            metadata = CSCateringMeta()
            cost_price = cost_price[0].strip() if cost_price else '0.00'
            metadata['cost_price'] = cost_price
            item['metadata'] = metadata

            category = loader.get_output_value('category').strip().lower()

            if category in ignore_categories and not self.has_sku(item.get('sku', '')):
                log.msg('Ignoring product %s because of category %s' % (loader.get_output_value('identifier'), category))
                continue

            yield Request(item['url'], callback=self.parse_img, meta={'item':item})

    def parse_img(self, response):
        hxs = HtmlXPathSelector(response)
        item = response.meta['item']
        item['image_url'] = ''.join(hxs.select('//div[contains(@class, "product-image")]/a/@href').extract())
        yield item
