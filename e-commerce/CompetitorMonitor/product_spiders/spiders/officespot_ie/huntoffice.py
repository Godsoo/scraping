import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from urllib import urlencode
import hashlib

import csv

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class HuntOfficeSpider(BaseSpider):
    name = 'huntoffice.ie'
    allowed_domains = ['www.huntoffice.ie', 'huntoffice.ie']
    start_urls = ('http://www.huntoffice.ie/site-directory.php',)

    def __init__(self, *args, **kwargs):
        super(HuntOfficeSpider, self).__init__(*args, **kwargs)
        self.skus = {}
        with open(os.path.join(HERE, 'skus.csv'), 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                self.skus[row[2].lower()] = row[0].lower()

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
                    return
        hxs = HtmlXPathSelector(response)

        # categories
        categories = hxs.select(u'//div[@id="page-holder"]/div[@class="all-col"]//ul//li//a/@href').extract()
        categories += hxs.select(u'//td[@class="category-cell"]//a/@href').extract()
        categories += hxs.select('//a[contains(@class, "subcategories_link")]/@href|//ul[contains(@class, "inner-cat")]//a/@href').extract()
        for url in categories:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url)

        # pagination
        next_page = hxs.select(u'//a[child::img[@alt="Next page"]]/@href').extract()
        if next_page:
            next_page = urljoin_rfc(get_base_url(response), next_page[0])
            yield Request(next_page)

        # products
        products = [url for url in hxs.select(u'//div[@id="gallery"]//h3/a/@href').extract() if 'javascript' not in url]
        products += hxs.select(u'//td[@class="product"]//h4/a/@href').extract()
        products += hxs.select('//div[@class="new-products-list"]//h4/a/@href').extract()
        for url in products:
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), response=response)
        product_loader.add_value('url', response.url)
        external_sku = hxs.select('//*[@id="product_code"]/text()').extract()
        if external_sku:
            external_sku = external_sku[0].strip()
            sku = self.skus.get(external_sku)
            product_loader.add_value('sku', sku or external_sku)

        product_loader.add_xpath('name', u'//h1[@itemprop="name"]/text()')
        product_loader.add_xpath('price', u'//*[@itemprop="price"]/@content')
        product_loader.add_xpath('identifier', u'//input[@name="productid"][1]/@value')
        brand = hxs.select('//div[contains(@class, "pr_spec") and h2[contains(text(), '
                           '"Product Specification")]]//dt[contains(text(), "Brand")]'
                           '/following-sibling::dd/text()').extract()
        if brand:
            product_loader.add_value('brand', brand[0].strip())

        product_loader.add_xpath('category', '//a[@class="bread-crumb"]/text()')
        product_loader.add_xpath('image_url', u'//img[@id="product_thumbnail"]/@src')

        yield product_loader.load_item()
