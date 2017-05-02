from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc, add_or_replace_parameter
from scrapy.utils.response import get_base_url

from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

import re
import os
import csv

from madeitem import MadeMeta
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider


HERE = os.path.abspath(os.path.dirname(__file__))

class MadeSpider(BaseSpider):
    name = 'made.com'
    allowed_domains = ['made.com']
    start_urls = ['http://www.made.com']
    items = {}

    def _start_requests(self):
        yield Request('http://www.made.com/bedding-and-bath/dipped-200tc-egyptian-cotton-stonewash-bed-set-elephant-grey', callback=self.parse_product)

    made_products = {}

    def __init__(self, *args, **kwargs):
        BaseSpider.__init__(self, *args, **kwargs)
        dispatcher.connect(self.process_pending, signals.spider_idle)

        self.run_num = 1

    def start_requests(self):
        file_path = HERE+'/made_products.csv'
        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.made_products[row['SKU'].upper().strip()] = row
 
        for start_url in self.start_urls:
            yield Request(start_url)

    def process_pending(self, spider):
        if spider != self: return
        self.run_num += 1
        if self.items:
            self.crawler.engine.schedule(Request(self.start_urls[0], callback=self.yield_items, dont_filter=True), spider) 
            raise DontCloseSpider('Found pending requests')
        if self.run_num == 2:
            self.crawler.engine.schedule(Request(self.start_urls[0], callback=self.parse2, dont_filter=True), spider)
            raise DontCloseSpider('Found pending requests')

    def yield_items(self, _):
        for i in self.items.values():
            yield i
        self.items = {}

    def parse(self, response):
        """ First process "Shop by type" sub-categories """
        hxs = HtmlXPathSelector(response)

        for main_cat_el in hxs.xpath('//ul[@id="top-nav"]/li[@id!="nav-new-in" and @id!="nav-last-chance"]'):
            if not main_cat_el.xpath("a/span/text()").extract():
                continue
            main_cat = main_cat_el.xpath("a/span/text()").extract()[0].strip()
            # following xpath extracts subcategories from "Shop by type" section only
            for subcat_el in main_cat_el.xpath('.//ul[@class="sub"]/li[1]//ul/li[@class="nav-list-item"]'):
                subcat = subcat_el.xpath('a/span/text()').extract()[0].strip()
                cats = [main_cat, subcat]
                url = subcat_el.xpath('a/@href').extract()[0]
                yield Request(url, callback=self.parse_cat, meta={'cats': cats})

    def parse2(self, response):
        """ Process general categories """
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[@id="top-nav"]/li[@id!="nav-new-in" and @id!="nav-last-chance"]//a[@class="level0"]/@href').extract():
            yield Request(url, callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//h3[@class="product-name"]//a/@href').extract():
            yield Request(url, callback=self.parse_product, dont_filter=True, meta=response.meta)

        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(url, callback=self.parse_cat, meta=response.meta)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        if not loader.get_output_value('identifier'):
            loader.add_xpath('identifier', 'substring-after(//span[starts-with(@id,"product-price-")]/@id, "product-price-")')
        loader.add_xpath('sku', '//div[@class="tr"]/div[@class="th" and contains(text(),"SKU")]/../div[contains(@class, "td")]/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@itemprop="name"]//text()')
        loader.add_xpath('image_url', '//meta[@itemprop="image"]/@content')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        loader.add_xpath('shipping_cost', '//div[@class="th" and contains(text(),"Standard delivery")]//following-sibling::div[@class="td"]/span[@class="price"]/text()')
        if not loader.get_output_value('name'):
            return
        if loader.get_output_value('name').split()[0] == '2':
            loader.add_value('brand', 'Flynn')
        else:
            loader.add_value('brand', loader.get_output_value('name').split()[0])

        if hxs.select('//span[@itemprop="availability" and @content="in_stock"]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        sku = loader.get_output_value('sku')
        sku = sku.upper().strip() if sku else ''
        made_product = self.made_products.get(sku, None)

        cats = response.meta.get('cats')
        no_category = False
        if not cats:
            if made_product:
                loader.add_value('category', made_product['Category'])
            else:
                loader.add_xpath('category', '//div[@class="breadcrumbs"]/ul/li[position()>1]/a/span/text()')
                if not loader.get_output_value('category'):
                    loader.add_value('category', (x.replace('-', ' ') for x in response.url.split('/')[3:-1]))
                    no_category = True
        else:
            loader.add_value('category', cats)

        product = loader.load_item()

        catmap = {
                "bedding and bath": "Bed & Bath",
                "beds": "Beds",
                "chairs": "Chairs",
                "homewares accessories": "Home Accessories",
                "lighting": "Lighting",
                "sofas and armchairs": "Sofas",
                "storage": "Storage",
                "tables": "Tables",
        }
        product['category'] = catmap.get(product['category'], product['category'])

        metadata = MadeMeta()
        metadata['johnlewis_code'] = made_product['JL product code'] if made_product else ''
        metadata['next_code'] = made_product['Next product code'] if made_product else ''
        product['metadata'] = metadata

        trs = hxs.select('//table[@id="super-product-table"]//tr/td[@class="price"]/..')
        if not trs:
            for x in self.yield_product(product, no_category):
                yield x
            return

        for tr in trs:
            loader = ProductLoader(item=Product(product), selector=tr)
            loader.add_xpath('identifier', 'substring-after(.//span[starts-with(@id,"product-price-")]/@id, "product-price-")')
            loader.add_value('name', product['name'])
            loader.add_xpath('name', './/td[1]/text()')
            loader.add_xpath('price', './/span[@property="price"]/@content')
            for x in self.yield_product(loader.load_item(), no_category):
                yield x

    def yield_product(self, product, no_category):
        if no_category:
            self.items[product['identifier']] = product
        else:
            if product['identifier'] in self.items:
                del self.items[product['identifier']]
            yield product

