from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
import os
import csv
from product_spiders.utils import extract_price_eu
from madeitem import MadeMeta
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from scrapy.exceptions import DontCloseSpider


HERE = os.path.abspath(os.path.dirname(__file__))


class MadeDeSpider(BaseSpider):
    name = 'made.de'
    allowed_domains = ['made.com']
    start_urls = ['http://www.made.com/de/']
    items = {}

    made_products = {}

    def __init__(self, *args, **kwargs):
        BaseSpider.__init__(self, *args, **kwargs)
        dispatcher.connect(self.process_pending, signals.spider_idle)

    def start_requests(self):
        file_path = HERE + '/made_products.csv'
        with open(file_path) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.made_products[row['SKU'].upper().strip()] = row

        for start_url in self.start_urls:
            yield Request(start_url)

    def process_pending(self, spider):
        if spider != self: return
        if self.items:
            self.crawler.engine.schedule(Request(self.start_urls[0], callback=self.yield_items, dont_filter=True), spider)
            raise DontCloseSpider('Found pending requests')

    def yield_items(self, _):
        for i in self.items.values():
            yield i
        self.items = {}

    def parse(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//ul[@id="top-nav"]/li[@id!="nav-new-in" and @id!="nav-last-chance"]//a[@class="level0"]/@href').extract():
            yield Request(url, callback=self.parse_cat)

    def parse_cat(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select('//h3[@class="product-name"]//a/@href').extract():
            yield Request(url, callback=self.parse_product, dont_filter=True)

        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(url, callback=self.parse_cat)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        if not loader.get_output_value('identifier'):
            loader.add_xpath('identifier', 'substring-after(//span[starts-with(@id,"product-price-")]/@id, "product-price-")')
        loader.add_xpath('sku', '//tr/th[contains(text(),"Artikelnummer")]/../td/text()')
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//div[@itemprop="name"]//text()')
        loader.add_xpath('image_url', '//meta[@itemprop="image"]/@content')
        loader.add_xpath('price', '//meta[@itemprop="price"]/@content')
        shipping_cost = hxs.select('//th[contains(text(),"Standardlieferpreis")]//following-sibling::td/span[@class="price"]/text()').extract()
        if shipping_cost:
            loader.add_value('shipping_cost', extract_price_eu(shipping_cost[0]))
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

        no_category = False
        if made_product:
            loader.add_value('category', made_product['Category'])
        else:
            loader.add_xpath('category', '//div[@class="breadcrumbs"]/ul/li[position()>1]/a/span/text()')
            if not loader.get_output_value('category'):
                loader.add_value('category', (x.replace('-', ' ') for x in response.url.split('/')[3:-1]))
                no_category = True

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
