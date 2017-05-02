import csv
import os
import shutil
from datetime import datetime
import StringIO

from scrapy.spider import BaseSpider
from scrapy import signals
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))

class RsOnlineSpider(BaseSpider):
    """
    Lucas:
    my suggestion is to increase the number of concurrent requests for that spider along with using Tor
    so that we don't get blocked. To increase the number of concurrent connection seems that there are two settings:
    http://doc.scrapy.org/en/0.9/topics/settings.html#concurrent-requests both of them would need to be changed.
    The thing is that those settings should be changed within the spider, so that it just affects that spider.
    My suggestion would be to use a value between 50 and 100 for both of those settings

    """
    name = 'arco-rs-online.com'
    allowed_domains = ['rs-online.com']

    concurrent_requests = 100
    concurrent_requests_per_domain = 100

    def __init__(self, *args, **kwargs):
        super(RsOnlineSpider, self).__init__(*args, **kwargs)
        self.prods_count = 0

    def start_requests(self):
        yield Request('http://uk.rs-online.com/web/op/all-products/', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//div[@class="productHierarchyDiv"]//a/@href').extract()
        for cat in cats:
            yield Request(urljoin_rfc(get_base_url(response), cat), callback=self.parse_subcats_full)

    def parse_subcats_full(self, response):
        hxs = HtmlXPathSelector(response)

        subcats = hxs.select('//div[@id="categories"]//a/@href').extract()
        for cat in subcats:
            url = urljoin_rfc(get_base_url(response), cat)
            if not url.endswith('/'):
                url += '/'
            url += '?sort-by=P_manufacturerPartNumber&sort-order=asc&view-type=List&sort-option=Manufacturers+Part+Number'
            yield Request(url, callback=self.parse_subcats_full)

        next_page = hxs.select('//div[@class="pagination"]//a[child::span[text()="Next"]]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(get_base_url(response), next_page[0]), callback=self.parse_subcats_full)

        for product in self.parse_product_list(response):
            yield product

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@id="mainContent"]//tr[starts-with(@id,"list")]')

        for product in products:
            name = product.select('.//a[img]/@title').extract()
            url = product.select('.//a[img]/@href').extract()
            url = urljoin_rfc(get_base_url(response), url[0])
            brand = "".join(product.select('.//div[@class="brandPartNoDiv"]/text()').extract()).strip()
            price = product.select('.//td[@class="listPrice"]//span[@class="nowprice"]/text()').extract()
            if not price:
                price = product.select('.//td[@class="listPrice"]/span[1]/text()').extract()
            category = hxs.select('//div[@class="breadCrumb rsGARealEstate"]//li/a/text()').extract()[-1].strip()
            sku = product.select('.//td[1]/a/text()').extract()

            loader = ProductLoader(selector=hxs, item=Product())
            loader.add_value('name', name)
            loader.add_value('url', url)
            loader.add_value('brand', brand)
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', sku)

            yield loader.load_item()

            self.prods_count += 1
            continue

            # url = product.select('.//td[1]/a/@href')[0].extract()
            # url = urljoin_rfc(get_base_url(response), url)
            # yield Request(url, callback=self.parse_product)
            #
            # loader = ProductLoader(selector=product, item=Product())
            # loader.add_xpath('name', './/td[1]/a/text()')
            # loader.add_xpath('sku', './/td[1]/a/text()')
            # loader.add_value('url', url)
            # loader.add_xpath('price', './/td[@class="listPrice"]//span[@class="nowprice"]/text()')
            # if not loader.get_output_value('price'):
            #     loader.add_xpath('price', './/td[@class="listPrice"]/span[1]/text()')
            #
            # yield loader.load_item()

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(selector=hxs, item=Product())
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1/span[@itemprop="name"]/text()')
        loader.add_xpath('brand', '//span[@itemprop="brand"]/a/span/text()')
        loader.add_xpath('price', '//tr[@class="dr-table-row rich-table-row dr-table-firstrow rich-table-firstrow odd"]//span[@itemprop="price"]/span/text()')
        loader.add_xpath('sku', '//span[@itemprop="mpn"]/text()')
        loader.add_xpath('identifier', '//span[@itemprop="mpn"]/text()')
        category = hxs.select('//div[@class="breadCrumb rsGARealEstate"]//li/a/text()').extract()[-1].strip()
        loader.add_value('category', category)
        yield loader.load_item()
