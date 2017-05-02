import time
import re
import urllib
from datetime import datetime
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


from sigmasportitems import SigmaSportMeta, extract_exc_vat_price


class TweeksSpider(SecondaryBaseSpider):
    name = 'sigmasport-tweekscycles.com'
    allowed_domains = ['tweekscycles.com']
    start_urls = ['http://www.tweekscycles.com/']

    csv_file = 'pedalpedal/tweekscycles_products.csv'
    # ignoring the json file because we don't need the metadata and it contains items from previous crawls
    #json_file = 'pedalpedal/tweekscycles_metadata.json'

    def preprocess_product(self, item):
        metadata = SigmaSportMeta()
        if not item['price']:
            item['price'] = '0.00'
        elif extract_price(item['price']) < 9:
            item['shipping_cost'] = 1.99
        metadata['price_exc_vat'] = extract_exc_vat_price(item)
        item['metadata'] = metadata
        return item