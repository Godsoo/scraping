import json
import shutil
import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url
from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))


class MobicitySpider(BaseSpider):
    """
    At the moment (02.05.2013) website has an issue - accessories category
    does not work properly. The workaround to this is using results of
    previous crawl to get products list. Also, just in case uses results
    of one old crawl as base - in case on previous crawl there will be
    not all products available.
    """
    name = "mobicity.co.nz"
    allowed_domains = ["www.mobicity.co.nz", ]
    start_urls = [
        "http://www.mobicity.co.nz/phones.html",
        "http://www.mobicity.co.nz/tablets.html",
        "http://www.mobicity.co.nz/more-mobile-phones.html",
        "http://www.mobicity.co.nz/mobile-phone-accessories.html"
        ]

    download_timeout = 300

    old_products_filename = 'mobicity_products.csv'
    main_products_filename = 'mobicity_products_main.csv'

    old_products = []
    main_products = []

    old_processed = False

    processed_products = []

    def __init__(self, *args, **kwargs):
        super(MobicitySpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)
        dispatcher.connect(self.spider_idle, signals.spider_idle)

        old_products_filename = os.path.join(HERE, self.old_products_filename)
        if os.path.exists(old_products_filename):
            with open(old_products_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.old_products.append(row)
                        
        main_products_filename = os.path.join(HERE, self.main_products_filename)
        if os.path.exists(main_products_filename):
            with open(main_products_filename) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.main_products.append(row)

    def spider_closed(self, spider, reason):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, self.old_products_filename))

    def spider_idle(self, spider):
        if not self.old_processed:
            for product in self.old_products:
                if product['identifier']:
                    identifier = product['identifier']
                else:
                    identifier = product['name']
                if not identifier in self.processed_products:
                    request = Request(
                        url=product['url'],
                        meta={"cat_name": product['category']},
                        callback=self.parse_product
                    )
                    self._crawler.engine.crawl(request, self)
        else:
            for product in self.main_products:
                if product['identifier']:
                    identifier = product['identifier']
                else:
                    identifier = product['name']
                if not identifier in self.processed_products:
                    request = Request(
                        url=product['url'],
                        meta={"cat_name": product['category']},
                        callback=self.parse_product
                    )
                    self._crawler.engine.crawl(request, self)

    def item_scraped(self, item, response, spider):
        if item['identifier']:
            identifier = item['identifier']
        else:
            identifier = item['name']
        self.processed_products.append(identifier)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        pages = set(hxs.select('//*[@class="pages"]//a/@href').extract())

        for page in pages:
            yield Request(urljoin_rfc(base_url, page))

        cat_name = hxs.select(
            "//div[@class='page-title category-title']/h1/text()").extract()

        # Dive in product, if it is
        products = hxs.select(
            "//div[@class='category-products']/ul/li/h2/a/@href").extract()
        if products:
            for product in products:
                yield Request(
                    url=canonicalize_url(product),
                    meta={"cat_name": cat_name},
                    callback=self.parse_product)

    def parse_product(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        # identifier =
        url = response.url
        # sku =
        # metadata =
        category = response.meta["cat_name"]
        image_url = hxs.select(
            "//div[contains(@class, 'product-img-box')]"
            "/p[contains(@class, 'product-image')]/img/@src").extract()
        # brand =
        # shipping_cost =

        colours = hxs.select("//div[@class='colours']//input").extract()
        if colours and len(colours) > 1:
            _script = hxs.select(
                "//script[contains(text(), 'spConfig')]/text()"
                ).extract()[0].split("(")
            script = "".join(_script[1:]).split(',"priceFromLabel"')[0] + '}'
            js = json.loads(script)
            for s in js['attributes']['76']['options']:
                color = s['label']
                code = s['products'][0]
                u = js['childProducts'].get(code)

                name = hxs.select(
                    "//div[@class='product-name']/h1/text()"
                    ).extract()[0] + " " + color
                price = u['finalPrice']
                if not price:
                    price = ""

                l = ProductLoader(response=response, item=Product())
                # l.add_value('identifier', identifier)
                l.add_value('url', url)
                l.add_value('name', name)
                l.add_value('price', price)
                # l.add_value('sku', sku)
                # l.add_value('metadata', metadata)
                l.add_value('category', category)
                l.add_value('image_url', image_url)
                # l.add_value('brand', brand)
                # l.add_value('shipping_cost', shipping_cost)
                yield l.load_item()
        else:
            name = hxs.select(
                "//div[@class='product-name']/h1/text()").extract()
            price = hxs.select(
                "//div[@class='price-box']//span[@class='regular-price']"
                "/span/text()").extract()
            if not price:
                price = ""

            l = ProductLoader(response=response, item=Product())
            # l.add_value('identifier', identifier)
            l.add_value('url', url)
            l.add_value('name', name)
            l.add_value('price', price)
            # l.add_value('sku', sku)
            # l.add_value('metadata', metadata)
            l.add_value('category', category)
            l.add_value('image_url', image_url)
            # l.add_value('brand', brand)
            # l.add_value('shipping_cost', shipping_cost)
            yield l.load_item()
