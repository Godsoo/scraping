import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)
from product_spiders.config import DATA_DIR
from product_spiders.utils import extract_price_eu

HERE = os.path.abspath(os.path.dirname(__file__))


class BrickshopNlSpider(BaseSpider):
    name = 'lego_nl_brickshop_nl'
    allowed_domains = ['brickshop.nl']
    start_urls = ['http://www.brickshop.nl/winkel.html']

    def __init__(self, *args, **kwargs):
        super(BrickshopNlSpider, self).__init__(*args, **kwargs)

    def start_requests(self):
        if hasattr(self, 'prev_crawl_id'):
            products_filename = os.path.join(DATA_DIR, '%s_products.csv' % self.prev_crawl_id)

            with open(os.path.join(HERE, products_filename)) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    yield Request(row['url'], callback=self.parse_product)

        # Scrape start urls
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[@id="vmMainPage"]//table//a[contains(@href, "lego") or '
                                'contains(@href, "duplo")]/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        for item in self.parse_category(response):
            yield item

    def parse_category(self, response):
        if response.url.endswith(".jpg"):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        if hxs.select('//table[@id="productDetailsTable"]'):
            for p in self.parse_product(response):
                yield p
            return

        products = hxs.select('//h2[@class="browseProductTitle"]//a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)

        pages = hxs.select('//ul[@class="pagination"]//a/@href').extract()
        for url in pages:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

        if not products and not pages:
            sub_cats = hxs.select('//div[@id="vmMainPage"]//table//a/@href').extract()
            for url in sub_cats:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        price = hxs.select('//*[@id="productDetailsTable"]//td[@class="vmCartContainer_td"]'
                           '/span[@class="productPrice"]/text()').extract()

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//*[@id="productDetailsTable"]//h1/text()')
        loader.add_value('price', extract_price_eu(price[0]) if price else '0.0')
        loader.add_xpath('identifier', '//input[@name="product_id"]/@value')
        loader.add_xpath('sku', '//*[@id="productDetailsTable"]//h1/text()', re=r'(\d{3,})')
        loader.add_xpath('image_url', '//*[@id="productDetailsTable"]/tr[2]/td[1]/a[1]/img/@src|'
                                      '//*[contains(@rel, "lightbox[product")]/img/@src')
        loader.add_value('url', response.url)

        yield loader.load_item()
