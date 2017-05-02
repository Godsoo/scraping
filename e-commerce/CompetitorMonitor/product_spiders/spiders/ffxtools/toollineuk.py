# -*- coding: utf-8 -*-
"""
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/3924-ffx-tools---new-site---tool-line-uk#/activity/ticket:
This spider extracts all the items from the website, all categories are crawled from both the sitemap and the category navigation bar.
"""

import os
import re
from decimal import Decimal
from product_spiders.base_spiders.primary_spider import PrimarySpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class ToolLineUKSpider(PrimarySpider):
    name = 'ffxtools-toollineuk.com'
    allowed_domains = ['toollineuk.com']
    start_urls = ['http://www.toollineuk.com/']
    crawl_search_results = True
    crawled_ids = []

    csv_file = 'toollineuk.com_products.csv'

    def __init__(self, *args, **kwargs):
        super(ToolLineUKSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

    def spider_idle(self, spider):
        if spider != self: return
        if self.crawl_search_results:
            self.crawl_search_results = False
            request = Request('http://www.toollineuk.com/search.php?search=', callback=self.parse_search)
            self._crawler.engine.crawl(request, self)
            raise DontCloseSpider('Starting search results crawl')

    def start_requests(self):
        urls = ['http://www.toollineuk.com/', 'http://www.toollineuk.com/productindex.php']
        for url in urls:
            yield Request(url)

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = 'http://www.toollineuk.com/' #get_base_url(response)
        products = hxs.select('//td[@class="prod_preview_title"]/a[@class="prodlink"]/@href').extract()
        for url in products:
            identifier = re.search('/sn/(.*)', url)
            identifier = identifier.group(1) if identifier else None
            if identifier and identifier in self.crawled_ids:
                continue
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        #pagination
        next_url = hxs.select('//a[@class="nextprev"]/@href').extract()[-1]
        yield Request(urljoin_rfc(base_url, next_url), callback=self.parse_search)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = 'http://www.toollineuk.com/' #get_base_url(response)

        categories = hxs.select('//ul[@id="css_vertical_menu"]//a/@href').extract()
        categories += hxs.select('//a[@class="catlink"]/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category))

        subcategories = hxs.select('//div[@class="catimagebox"]/a/@href').extract()
        for subcategory in subcategories:
            yield Request(urljoin_rfc(base_url, subcategory))

        products = hxs.select('//td[@class="prod_preview_title"]/a[@class="prodlink"]/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        loader = ProductLoader(item=Product(), selector=hxs)
        name = hxs.select('//tr[@class="mainprodboxtitle"]/td/h1/text()').extract()
        loader.add_value('name', name)
        loader.add_value('url', response.url)

        stock = hxs.select('//div[@class="mainprodbox"]//input[@type="image" and @alt="Buy"]')
        if not stock:
            loader.add_value('stock', 0)

        price = hxs.select('//div[@class="mainprodbox"]//span[@class="buyprice"]/text()').extract()
        if not price:
            price = hxs.select('//table[@class="buybox"]//td[@align="right" and @class="buyboxlightblue"]/text()').extract()
        if price:
            loader.add_value('price', price)
        else:
            loader.add_value('price', '0.00')

        price = loader.get_output_value('price')
        if Decimal(price or '0.00') < Decimal('50.00'):
            loader.add_value('shipping_cost', '4.95')

        brand = hxs.select('//img[contains(@src,"logo")]/@alt').extract()
        loader.add_value('brand', brand)

        categories = hxs.select('//tr[@class="mainprodboxtitle"]/td/a/text()').extract()
        for category in categories:
            loader.add_value('category', category)

        sku = hxs.select('//div[@class="mainprodbox"]//td[@class="text_small"]/text()').re('Product Code: (.*)')
        loader.add_value('sku', sku)

        identifier = hxs.select('//div[@class="mainprodbox"]//input[@type="hidden" and @name="sn"]/@value').extract()
        if not identifier:
            identifier = re.search('/sn/(.*)', response.url)
            identifier = identifier.group(1) if identifier else None
        else:
            identifier = identifier[0]
        loader.add_value('identifier', identifier)

        image_url = hxs.select('//div[@class="mainprodbox"]//a[contains(@href,"popup")]/img/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))

        self.crawled_ids.append(identifier)

        yield loader.load_item()
