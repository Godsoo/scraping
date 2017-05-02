import csv
import os
import shutil
import StringIO
import urllib
from datetime import datetime

from scrapy import log
from scrapy import signals
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import CloseSpider

from product_spiders.items import Product, ProductLoader

HOME = os.path.abspath(os.path.dirname(__file__))


class OnlinePharmacySpider(BaseSpider):
    name = "onlinepharmacy.com.au"
    allowed_domains = [
        "www.onlinepharmacy.com.au",
        "www.pharmacyonline.com.au",
        'competitormonitor.com',]
    """start_urls = [
        "http://www.onlinepharmacy.com.au",
        ]"""

    # ======================================================================
    # INITIALS
    def __init__(self, *args, **kwargs):
        super(OnlinePharmacySpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy(
                "data/%s_products.csv" % spider.crawl_id,
                os.path.join(HOME, "onlinepharmacy_products.csv"))

    def full_run_required(self):
        if not os.path.exists(
            os.path.join(HOME, "onlinepharmacy_products.csv")):
            return True

        #run full only on Mondays
        return datetime.now().weekday() == 1

    def start_requests(self):
        if self.full_run_required():
            start_req = self._start_requests_full()
            log.msg(">>> Full run")
        else:
            start_req = self._start_requests_simple()
            log.msg(">>> Simple run")

        for req in start_req:
            yield req

    def _start_requests_full(self):
        yield Request(
            url="http://www.pharmacyonline.com.au",
            callback=self.parse_full)

    def _start_requests_simple(self):
        yield Request(
            url="http://competitormonitor.com/login.html"
                "?action=get_products_api&website_id=470333&matched=1",
            callback=self.parse_simple)

    # ======================================================================
    # FULL PARSING
    def parse_full(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select(
            "//div[@class='nav-container']/ul[@id='nav']/li/a/@href"
            ).extract()
        for cat in cats:
            yield Request(
                url=canonicalize_url(cat),
                callback=self.parse_subcat)

    def parse_subcat(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        subcats = hxs.select("//div[@class='subcats']/ul/li/h4/a/@href"
            ).extract()
        if subcats:
            for subcat in subcats:
                yield Request(
                    url=canonicalize_url(subcat),
                    callback=self.parse_subcat)

        cat_name = hxs.select(
            "//div[@class='category_head']/div[@class='cat_title']/h1/text()"
            ).extract()
        next_page = hxs.select(
            "//div[@class='pages']/ol/li/a[@title='Next']/@href"
            ).extract()
        if next_page:
            yield Request(
                url=canonicalize_url(next_page[0]),
                callback=self.parse_subcat)

        # Dive in product, if it is
        products = hxs.select("//div[@class='category-products']"
            "/ul/li/a[2]/@href"
            ).extract()
        if products:
            for product in products:
                yield Request(
                    url=canonicalize_url(product),
                    meta={"cat_name": cat_name},
                    callback=self.parse_products)

    def parse_products(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        #identifier =
        url = canonicalize_url(response.url)
        name = hxs.select("//div[@class='product-name']/h1/text()"
            ).extract()[0].strip()
        price = hxs.select(
            "//div[@class='pricing']/div[@class='m-price']/span/text()"
            ).extract()
        if not price:
            price = ""
        sku = hxs.select("//div[@class='product-name']/p/text()"
            ).extract()[0].split(" ")[1]
        #metadata =
        category = response.meta["cat_name"]
        image_url = hxs.select("//div[@class='main_image']/a/img/@src"
            ).extract()
        if not image_url:
            image_url = hxs.select(
                "//div[@class='product-img-box']/p/img/@src").extract()
            if not image_url:
                image_url = ""
        #brand =
        #shipping_cost =

        l = ProductLoader(response=response, item=Product())
        #l.add_value('identifier', identifier)
        l.add_value('url', url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('sku', sku)
        #l.add_value('metadata', metadata)
        l.add_value('category', category)
        l.add_value('image_url', image_url)
        #l.add_value('brand', brand)
        #l.add_value('shipping_cost', shipping_cost)
        yield l.load_item()

    # ======================================================================
    # SIMPLE PARSING
    def parse_simple(self, response):
        f = StringIO.StringIO(response.body)
        hxs = HtmlXPathSelector()
        reader = csv.DictReader(f)
        self.matched = set()

        for row in reader:
            self.matched.add(row['url'])

        for url in self.matched:
            yield Request(
                url=url,
                callback=self.parse_product)

        with open(os.path.join(HOME, 'onlinepharmacy_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row['url'] not in self.matched:
                    loader = ProductLoader(selector=hxs, item=Product())
                    loader.add_value('identifier', row['identifier'])
                    loader.add_value('url', row['url'])
                    loader.add_value('name', row['name'])
                    loader.add_value('price', row['price'])
                    loader.add_value('sku', row['sku'])
                    loader.add_value('category', row['category'])
                    loader.add_value('image_url', row['image_url'])
                    loader.add_value('brand', row['brand'])
                    loader.add_value('shipping_cost', row['shipping_cost'])
                    yield loader.load_item()

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # Fill up the Product model fields
        #identifier =
        url = canonicalize_url(response.url)
        name = hxs.select("//div[@class='product-name']/h1/text()"
            ).extract()[0].strip()
        price = hxs.select(
            "//div[@class='pricing']/div[@class='m-price']/span/text()"
            ).extract()
        if not price:
            price = ""
        sku = hxs.select("//div[@class='product-name']/p/text()"
            ).extract()[0].split(" ")[1]
        #metadata =
        #category =
        #image_url =
        #brand =
        #shipping_cost =

        l = ProductLoader(response=response, item=Product())
        #l.add_value('identifier', identifier)
        l.add_value('url', url)
        l.add_value('name', name)
        l.add_value('price', price)
        l.add_value('sku', sku)
        #l.add_value('metadata', metadata)
        #l.add_value('category', category)
        #l.add_value('image_url', image_url)
        #l.add_value('brand', brand)
        #l.add_value('shipping_cost', shipping_cost)
        yield l.load_item()
