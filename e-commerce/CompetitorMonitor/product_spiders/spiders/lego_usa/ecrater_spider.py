import csv
import os
import copy
import re

import shutil

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, url_query_parameter
from scrapy import log

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.base_spiders.matcher import Matcher

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class EcraterSpider(BaseSpider):
    name = 'legousa-ecrater.com'
    allowed_domains = ['ecrater.com']
    start_urls = ('http://www.ecrater.com/filter.php?cid=542133&keywords=lego&slocation=d&new=1',
                  'http://www.ecrater.com/filter.php?cid=542133&slocation=d&new=1')
    _re_sku = re.compile('(\d\d\d\d\d?)')

    # Map deviation screenshot feature
    map_deviation_detection = True
    map_deviation_csv = os.path.join(HERE, 'ecrater_map_deviation.csv')

    def __init__(self, *args, **kwargs):
        super(EcraterSpider, self).__init__(*args, **kwargs)
        self.matcher = Matcher(self.log)
        with open(os.path.join(HERE, 'lego.csv')) as f:
            reader = csv.reader(f)
            self.products = {prod[2]:prod[3].decode('utf8') for prod in reader}

        dispatcher.connect(self.spider_closed, signals.spider_closed)

        if os.path.exists(os.path.join(HERE, 'ecrater_products.csv')):
            shutil.copy(os.path.join(HERE, 'ecrater_products.csv'),
                        os.path.join(HERE, 'ecrater_products.csv.bak'))

        # Errors
        self.errors = []

    def spider_closed(self, spider):
        shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'toysrus_products.csv'))

    def start_requests(self):
        # Parse default items and then start_urls
        yield Request('http://www.ecrater.com', self.parse_default)

    def parse_default(self, response):
        with open(os.path.join(HERE, 'ecrater_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield Request(row['url'], self.parse_product)

        # Scrape start urls
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next = hxs.select('//ul[@class="pagination-controls nav"]/li/a[@title="Next Page"]/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[-1]), callback=self.parse)

        products = hxs.select('//div[@class="product-details"]/h2/a/@href').extract()
        for product in products:
            if 'keywords=lego' in response.url or 'lego' in product:
                yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        if not products:
            self.errors.append('WARNING: No products in %s' % response.url)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        seller = hxs.select('//a[@class="seller-username"]/text()').extract()[0]

        cart_url = hxs.select('//div[@id="product-title-actions"]/a/@href').extract()[0]
        identifier = url_query_parameter(urljoin_rfc(base_url, cart_url), 'pid', None)

        if not identifier:
            identifier_regex = re.search(r'p/(\d+)/', response.url)
            if not identifier_regex:
                self.errors.append('WARNING: No identifier in %s' % response.url)
                return
            else:
                identifier = identifier_regex.groups()[0]

        name = hxs.select('//div[@id="product-title"]/h1/text()').extract()[0]

        sku = self._re_sku.findall(name)
        sku = sku[0] if sku else ''


        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('identifier', identifier + '-' + seller)
        loader.add_value('name', name)
        loader.add_value('brand', 'LEGO')
        loader.add_xpath('category', '//ul[@class="breadcrumb"]/li/a[@class="active"]/text()')
        loader.add_value('url', response.url)
        price = hxs.select('//div[@id="product-title-actions"]/span/text()').extract()[0]

        loader.add_value('price', price)
        image_url = hxs.select('//img[@id="product-image-display"]/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])


        stock = hxs.select('//p[@id="product-quantity"]/text()').extract()
        if stock:
            stock = re.findall("\d+", stock[0])
            stock = stock[0] if stock else 0
            loader.add_value('stock', stock)

        shipping = hxs.select('//p[a[@href="#shipping-rates"]]/text()').extract()
        if shipping:
            shipping = re.findall("\d+.\d+", shipping[0])
            shipping = shipping[0] if shipping else 0
            loader.add_value('shipping_cost', shipping)

        loader.add_value('dealer', seller)
        if sku in self.products.keys():
            if self.match_name(self.products[sku], name):
                loader.add_value('sku', sku)
            else:
                log.msg('###########################')
                log.msg(response.url)
                log.msg('###########################')
        else:
            loader.add_value('sku', sku)

        yield loader.load_item()

    def match_name(self, search_name, new_item, match_threshold=90, important_words=None):
        r = self.matcher.match_ratio(search_name, new_item, important_words)
        return r >= match_threshold
