"""
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4157
The spider uses CrawlSpider class with the rules.
The spider is parsing all products and check if product sku is present in the feed file.
Extracting only products present in the feed file.
"""
import json

from scrapy.http import Request
from scrapy.spiders import CrawlSpider, Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import HtmlXPathSelector
from urlparse import urljoin
from scrapy.utils.response import get_base_url

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
from scrapy.exceptions import DontCloseSpider

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader
from product_spiders.utils import extract_price
import csv
import os
from collections import defaultdict
from operator import itemgetter

HERE = os.path.abspath(os.path.dirname(__file__))

class Expert_Ireland(CrawlSpider):
    name = 'briscoes-expert_ireland'
    allowed_domains = ['expert.ie']
    start_urls = ['https://www.expert.ie']
    csv_file = HERE + '/expert_ireland_products.csv'
    shipping_costs_file = HERE + '/expert_ireland_shipping.csv'
    matched_identifiers = []
    
    rules = (
        Rule(LinkExtractor(restrict_xpaths=('//ul[@id="menuElem"]',
                                            '//a[@class="UnselectedPage"]',
                                            '//article[@class="product-tile brand-title"]'
                                            ))),
        Rule(LinkExtractor(restrict_xpaths='//a[@class="product-list-link"]'
                                            ), 
             callback='parse_product',
             follow=True)
        )
    
    def __init__(self, *args, **kwargs):
        super(Expert_Ireland, self).__init__(*args, **kwargs)
        dispatcher.connect(self.processing_products, signals.spider_idle)
        self.skus = set()
        with open(self.csv_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.skus.add(row['SKU'].strip().lower())
        self.log('Found %d products in the feed file' %len(self.skus))
        self.skus_parsed = set()
        self.products = defaultdict(list)

        self.shipping_costs = {}
        with open(self.shipping_costs_file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.shipping_costs[row['SKU'].strip().lower()] = row['Shipping Charge']

    def start_requests(self):
        yield Request('https://app.competitormonitor.com/api/get_matched_products.json?website_id=1852&api_key=3Df7mNg',
                      callback=self.parse_matches)

    def parse_matches(self, response):
        data = json.loads(response.body)
        matches = data['matches']
        for match in matches:
            self.matched_identifiers.append(match['identifier'])

        for url in self.start_urls:
            yield Request(url)
        
    def _parse(self, response):
        yield Request('https://www.expert.ie/products/tv-dvd/televisions/50-55-inch/panasonic-55-4k-led-tv-tx-55cx802b', callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        
        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('sku', '//script/@data-flix-sku')
        shipping_cost = self.shipping_costs.get(loader.get_output_value('sku'), None)
        if shipping_cost:
            loader.add_value('shipping_cost', extract_price(shipping_cost))
        
        loader.add_xpath('identifier', '//input[contains(@id, "SKUID")]/@value')
        name = response.xpath('//h1/text()').extract() or response.xpath('//h2[@itemprop="name"]/text()').extract()
        if not name:
            return
        name = name[0]
        loader.add_value('name', name)
        loader.add_xpath('price', '//span[@class="TotalPrice"]/text()')
        categories = response.xpath('//a[@class="CMSBreadCrumbsLink"]/text()').extract()
        if not categories:
            categories = ''
        loader.add_value('category', categories)
        for brand in hxs.select('//div[@title="Brand"]/following-sibling::div//span/@title').extract():
            if name.title().startswith(brand.title()):
                break
        else:
            brand = ''
        loader.add_value('brand', brand)
        loader.add_value('shipping_cost', 19.99)
        if 'In stock' not in hxs.select('//span[@class="stock available"]/text()').extract():
            loader.add_value('stock', 0)
        
        product = loader.load_item()
        self.products[product['sku']].append(product)
        
    def processing_products(self, spider):
        if self != spider or self.skus_parsed:
            return
        request = Request(self.start_urls[0], callback=self.yield_products, dont_filter=True)
        self.crawler.engine.crawl(request, spider)
        raise DontCloseSpider()
    
    def yield_products(self, response):
        self.logger.debug("%d SKU's collected" %len(self.products))
        for sku in self.products:
            if sku.lower() not in self.skus:
                continue
            self.skus_parsed.add(sku)
            products = sorted(self.products[sku], key=itemgetter('brand', 'category'))
            first_product = products.pop()
            if first_product['identifier'] in self.matched_identifiers:
                yield first_product
            for product in products:
                if product['name'].lower() != first_product['name'].lower() and product.get('brand') and product['identifier'] in self.matched_identifiers:
                    self.log('Duplicated SKU: %s' % sku)
                    yield product

        skus = self.skus - self.skus_parsed
        self.log("%d SKU's not parsed:" % len(skus))
        for sku in skus:
            self.log(sku)
        self.skus_parsed = True

