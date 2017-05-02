from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price
from scrapy.utils.response import get_base_url


class DjKit(BaseSpider):
    name = 'testmem'
    allowed_domains = ['djkit.com']
    start_urls = ['http://www.djkit.com']

    def parse(self, response):
        from guppy import hpy
        h = hpy()
        self.log(str(h.heap()))