import logging
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoader

class termoidraulica2006_spider(BaseSpider):
    name = 'termoidraulica2006.ebay'
    allowed_domains = ['www.ebay.it', 'stores.ebay.it', 'ebay.it', 'ebay.com']
    start_urls = ('http://stores.ebay.it/termoidraulica2006',)

    scraped_identifiers = []
    items_count = 0
    items_scraped = 0
    pages_count = 0
    tries = 0

    def __init__(self, *a, **kw):
        super(termoidraulica2006_spider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        dispatcher.connect(self.item_scraped, signals.item_scraped)

    def spider_idle(self, spider):
        logging.error("Total count: %d" % self.items_count)
        logging.error("Items scraped: %d" % self.items_scraped)
        if (self.items_count > self.items_scraped) and (self.tries < 5):
            logging.error("Not all scraped: found %d of %d" % (self.items_scraped, self.items_count))
            request = Request(self.start_urls[0], dont_filter=True)
            self._crawler.engine.crawl(request, self)
        else:
            logging.error("Scraped %d of %d. The rest are duplicates" % (self.items_scraped, self.items_count))
            logging.error("Finished on %d try" % self.tries)

    def item_scraped(self, item, response, spider):
        if spider == self:
            self.items_scraped += 1

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//td[@id="CentralArea"]//tr[@itemscope="itemscope"]')
        for p in products:
            try:
                name = p.select('td[@class="details"]/div[1]/a/@title')[0].extract()
            except IndexError:
                continue

            try:
                url = p.select('td[@class="details"]/div[1]/a/@href')[0].extract()
            except IndexError:
                continue

            try:
                price = p.select('td[contains(@class, "prices")]/text()').re(r'([0-9\.\, ]+)')[0]
            except IndexError:
                continue

            reg = 'hash=(.*)$'
            identifier = re.search(reg, url).group(1)

            if identifier in self.scraped_identifiers:
                continue

            self.scraped_identifiers.append(identifier)

            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', name.strip())
            product_loader.add_value('price', price.replace(".", "").replace(",", "."))
            product_loader.add_value('url', url)
            product_loader.add_value('identifier', identifier)
            yield product_loader.load_item()

    def main_parse(self, response):
        hxs = HtmlXPathSelector(response)

        items_count = hxs.select("//span[@class='smuy']/span[@class='countClass']/text()").extract()
        if not items_count:
            logging.error("Items count not found!")
            return
        self.items_count = int(items_count[0].replace(".", ""))

        self.pages_count = self.items_count / 30 + 1

        #pages
        for i in range(1, self.pages_count + 1):
            url = "http://stores.ebay.it/termoidraulica2006/_i.html?_pgn=" + str(i)
            yield Request(url, dont_filter=True, callback=self.parse_product)

    def parse(self, response):
        sorting_url = 'http://stores.ebay.it/termoidraulica2006/_i.html?rt=nc&_sid=934836408&_trksid=p4634.c0.m14&_sop=2&_sc=1'

        self.tries += 1
        logging.error("Try %d" % self.tries)

        if not isinstance(response, HtmlResponse):
            return

        yield Request(sorting_url, callback=self.main_parse, dont_filter=True)


