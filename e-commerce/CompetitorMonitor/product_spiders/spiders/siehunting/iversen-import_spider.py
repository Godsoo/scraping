import re
import os
import csv
import hashlib
import re

from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.selector import HtmlXPathSelector
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
from product_spiders.items import Product, ProductLoaderWithNameStrip\
                             as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class IversenImportSpider(CrawlSpider):

    name = 'iversen-import.dk'
    allowed_domains = ['iversen-import.dk']
    start_urls = ['http://www.iversen-import.dk/products/productlist.aspx?searchtext=+']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//table[@class="Tabular"]/tbody/tr')
        for product in products:
            loader = ProductLoader(item=Product(), selector=product)
            name = ''.join(product.select('td/a/img/@alt').extract())
            if not name:
                name = ''.join(product.select('td/a/text()').extract()[1:-1])
            loader.add_value('name', name)
            url = urljoin_rfc(get_base_url(response), product.select('td[@style="text-align: right;"]/a/@href').extract()[0])
            loader.add_value('url',url)
            price = ''.join(product.select('td[@style="text-align: right;"]/a/text()').extract()).replace('.','').replace(',','.')
            loader.add_value('price', price)
            yield loader.load_item()
        next = hxs.select('//a[@class="plistpagnext"]/@href').extract()
        if next:
            url = urljoin_rfc(get_base_url(response), next[0])
            yield Request(url)
