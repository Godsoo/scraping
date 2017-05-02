from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
# import copy
# import itertools


class CateringApplianceComSpider(SecondaryBaseSpider):
    name = 'caterkwik-catering-appliance.com'
    allowed_domains = ['catering-appliance.com']
    start_urls = ('http://www.catering-appliance.com/categories/',)

    csv_file = 'cscatering/cateringappliancecom_products.csv'