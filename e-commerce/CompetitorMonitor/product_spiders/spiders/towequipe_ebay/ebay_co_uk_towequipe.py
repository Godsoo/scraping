# -*- coding: utf-8 -*-

import os
import shutil
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoader

from items import TowequipeEbayMeta

HERE = os.path.abspath(os.path.dirname(__file__))

search_for = [
    'Witter',
]

class TowEquipeEbaySpider(BaseSpider):
    name = 'towequipe_ebay-ebay.co.uk_toqequipe'
    allowed_domains = [
        'www.ebay.co.uk',
        'stores.ebay.co.uk',
        'stores.shop.ebay.co.uk'
    ]
    start_urls = ('http://stores.ebay.co.uk/Fit-your-own-towbars-Towequipe',)

    scraped_urls = []
    items_count = 0
    items_scraped = 0
    pages_count = 0
    tries = 0
    
    items = []

    def __init__(self, *a, **kw):
        super(TowEquipeEbaySpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'ebay_towequipe_products.csv'))
            logging.error("CSV is copied")

    def spider_idle(self, spider):
        logging.error("Total count: %d" % self.items_count)
        logging.error("Items scraped: %d" % self.items_scraped)
        if (self.items_count > self.items_scraped) and (self.tries < 1):
            logging.error("Not all scraped: found %d of %d" % (self.items_scraped, self.items_count))
            request = Request(self.start_urls[0], dont_filter=True)
            self._crawler.engine.crawl(request, self)
        else:
            logging.error("Scraped %d of %d" % (self.items_scraped, self.items_count))
            logging.error("Finished on %d try" % self.tries)

        if self.items:
            request = Request(self.start_urls[0], dont_filter=True, callback=self.closing_parse)
            self._crawler.engine.crawl(request, self)

    def closing_parse(self, response):
        self.log("Processing items after finish")
        items_dict = {}
        items = sorted(self.items, key=lambda x: x['name'])
        for item in items:
            if item['sku'] in items_dict:
                old_item = items_dict[item['sku']]
                if item['price'] < old_item['price']:
                    items_dict[item['sku']] = item
            else:
                items_dict[item['sku']] = item

        self.items = []

        for sku, item in items_dict.items():
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', item['name'])
            loader.add_value('url', item['url'])
            loader.add_value('price', item['price'])
            loader.add_value('sku', item['sku'])
            loader.add_value('identifier', item['identifier'])
            product = loader.load_item()

            metadata = TowequipeEbayMeta()
            metadata['seller_id'] = item['seller_id']

            product['metadata'] = metadata
            yield product

    def parse(self, response):
        self.tries += 1
        logging.error("Try %d" % self.tries)
        for keyword in search_for:
            data = {
                '_nkw': keyword
            }
            req = FormRequest.from_response(
                response=response,
                formname='Search',
                formdata=data,
                callback=self.parse_search,
                dont_filter=True
            )
            yield req

    def parse_search(self, response):
        hxs = HtmlXPathSelector(response)

        total_count = hxs.select("//span[@class='smuy']/span[@class='countClass']/text()").extract()
        if not total_count:
            logging.error("Total count not found!!!")
            return
        total_count = int(total_count[0].replace(",", ""))
        self.items_count = total_count

        for p in range(1, total_count / 30 + 1 + 1):
            url = response.url + "&_pgn=" + str(p)
            yield Request(
                url,
                callback=self.parse_product_list,
                dont_filter=True
            )

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select("//a[@itemprop='name']/@href").extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(
                url,
                callback=self.parse_product
            )

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        url = response.url

        name = hxs.select("//*[@itemprop='name']/text()").extract()
        if not name:
            logging.error("NO NAME!!! %s" % response.url)
            return
        name = name[0]

        price = hxs.select("//*[@itemprop='price']/text()").extract()
        if not price:
            logging.error("NO PRICE!!! %s, %s" % (name, response.url))
            return
        price = price[0]

        if hxs.select("//td[contains(text(), 'MPN')]"):
            sku = hxs.select("//td[contains(text(), 'MPN')]")[0].select("following-sibling::td/text()[1]").extract()
        elif hxs.select("//td[contains(text(), 'Part Manufacturer Number')]"):
            sku = hxs.select("//td[contains(text(), 'Part Manufacturer Number')]")[0].select(
                "following-sibling::td/text()[1]").extract()
        else:
            logging.error("NO SKU!!! %s, %s" % (name, response.url))
            return
        sku = sku[0].strip()

        sku = sku.lower()

        if sku.startswith('witterkit-'):
            sku = sku[len('witterkit-'):]

        seller_id = hxs.select("//*[@class='mbg-nw']//text()").extract()
        if not seller_id:
            logging.error("NO SELLER ID!!! %s, %s" % (name, response.url))
            return
        seller_id = seller_id[0]
        
        product = {
            'name': name,
            'url': url,
            'price': price,
            'sku': sku,
            'identifier': sku,
            'seller_id': seller_id
        }

        if not product in self.items:
            self.items.append(product)
            self.items_scraped += 1

        # loader = ProductLoader(item=Product(), selector=hxs)
        # loader.add_value('name', name)
        # loader.add_value('url', url)
        # loader.add_value('price', price)
        # loader.add_value('sku', sku)
        # loader.add_value('identifier', sku)
        # product = loader.load_item()
        # product['metadata'] = metadata
        # yield product
