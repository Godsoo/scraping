import os
import csv

from scrapy.http import Request
from cStringIO import StringIO

from product_spiders.base_spiders.amazonspider2 import BaseAmazonSpider
from product_spiders.base_spiders.amazonspider2.scraper import AmazonUrlCreator

from scrapy import log

HERE = os.path.abspath(os.path.dirname(__file__))


class PowerhouseAmazonSpider(BaseAmazonSpider):
    name = 'powerhouse_fitness-amazon.co.uk'
    domain = "amazon.co.uk"
    allowed_domains = ['amazon.co.uk', 'powerhouse-fitness.co.uk']
    type = 'asins'
    all_sellers = True

    products = []

    def start_requests(self):
        feed_url = "http://www.powerhouse-fitness.co.uk/feeds/competitor_monitor_feed/powerhouse-competitor_monitor_feed.txt"
        yield Request(feed_url, callback=self.parse_feed)

    def parse_feed(self, response):
        reader = csv.reader(StringIO(response.body), delimiter="\t")
        for row in reader:
            self.products.append(row)

        for r in super(PowerhouseAmazonSpider, self).start_requests():
            yield r

    def get_asins_generator(self):
        for product in self.products:
            asin = product[-1]
            sku = product[0]
            if asin != '':
                yield asin, sku
