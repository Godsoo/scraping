import re
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse

from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals

from product_spiders.items import Product, ProductLoader

class anpa2011_spider(BaseSpider):
    name = 'anpa2011.ebay'
    allowed_domains = ['www.ebay.it', 'stores.ebay.it', 'ebay.it', 'ebay.com']
    start_urls = ('http://stores.ebay.it/anpa2011',)

    scraped_urls = []
    items_count = 0
    items_scraped = 0
    pages_count = 0
    tries = 0

    def __init__(self, *a, **kw):
        super(anpa2011_spider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_idle, signals.spider_idle)
        dispatcher.connect(self.item_scraped, signals.item_scraped)
        print self.start_urls

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

        products = hxs.select("//tr[@itemprop='offers']")
        logging.error("Debug. %s. Found %d products" % (response.url, len(products)))
        for p in products:
            try:
                name = p.select('.//a[@itemprop="name"]/@title')[0].extract()
            except IndexError:
                continue

            try:
                url = p.select('.//a[@itemprop="name"]/@href')[0].extract()
                identifier = re.search(r'/(\d+)\?', url).groups()[0]
            except IndexError:
                continue

            price = p.select('.//*[@itemprop="price"]/text()').re(r'([0-9\.\, ]+)')
            if not price:
                logging.error("No PRICE! %s %s" % (name, response.url))
                continue

            self.scraped_urls.append(url)

            product_loader = ProductLoader(item=Product(), response=response)
            product_loader.add_value('name', name.strip())
            product_loader.add_value('price', price[0].replace(".", "").replace(",", "."))
            product_loader.add_value('url', url)
            product_loader.add_value('identifier', identifier)
            yield product_loader.load_item()

    def parse(self, response):
        self.tries += 1
        logging.error("Try %d" % self.tries)

        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        items_count = hxs.select("//span[@class='smuy']/span[@class='countClass']/text()").extract()
        if not items_count:
            logging.error("Items count not found!")
            return
        self.items_count = int(items_count[0].replace(".", ""))

        self.pages_count = self.items_count / 30 + 1

        # pages
        for i in range(1, self.pages_count + 1):
            url = "http://stores.ebay.it/anpa2011/_i.html?_pgn=" + str(i)
            yield Request(url, dont_filter=True, callback=self.parse_product)
