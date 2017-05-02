import re
import json
import urlparse
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from scrapy import log

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.base_spiders.prodcache import ProductCacheSpider
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class AdvantageCateringEquipmentSpider(SecondaryBaseSpider):
    name = 'caterkwik-advantage-catering-equipment.co.uk'
    allowed_domains = ['advantage-catering-equipment.co.uk']
    start_urls = ('http://advantage-catering-equipment.co.uk',)

    csv_file = 'cscatering/advantage_catering_equipment_products.csv'