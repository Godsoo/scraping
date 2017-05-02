from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import urllib2
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class BejbySpider(LegoMetadataBaseSpider):
    name = u'bejby.net'
    allowed_domains = ['www.bejbynet.cz']
    start_urls = [
        u'http://www.bejbynet.cz/lego-4?page=1',
        u'http://www.bejbynet.cz/lego-nahradni-dily?page=1',
    ]
    errors = []
    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//div[@id="products"]//h2/a/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        if items:
            url = urllib2.urlparse.urlparse(base_url)
            new_url = url.scheme + "://" + url.netloc + url.path + "?page=%d" % (response.meta.get("n", 1) + 1)
            yield Request(new_url, callback=self.parse, meta={"n": response.meta.get("n", 1) + 1})

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+)\W*K.*', r'\1', price.strip())
        except TypeError:
            return False
        if count:
            price = price.replace(",", "").replace(" ", "")
            try:
                price = float(price)
            except ValueError:
                return False
            else:
                return price
        elif price.isdigit():
            return float(price)
        return False

    def get_sku_from_text(self, text):
        try:
            id, count = re.subn(r'[^0-9]*([0-9]{4,6}).*', r'\1', text)
        except TypeError:
            return ""
        if count:
            id = id.strip()
            try:
                int(id)
            except ValueError:
                return ""
            else:
                return id
        return False

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//h1[@id="title"]/text()').pop().extract().strip()

        category = hxs.select('//ul[@id="breadcrumbs"]/li/a/text()')[-1].extract().strip()

        sku = self.get_sku_from_text(name)

        pid = hxs.select('//div[@id="product-description"]//input[@name="product"]/@value').extract()[0]
        if not sku:
            sku = pid

        price = self.parse_price("".join(hxs.select('//span[contains(@class, "final-price")]/span/span[@class="price"]/text()').extract()))

        stock = hxs.select('//div[contains(@class, "product-prices")]//div[contains(@class, "availability")]/div[@class="green"]')

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            loader.add_xpath('image_url', '//img[@id="galeryImg"]/@src')
            loader.add_value('price', price)
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', pid)
            loader.add_value('brand', 'LEGO')
            if int(price) < 2000:
                loader.add_value('shipping_cost', 89)
            if not stock:
                loader.add_value('stock', 0)
            yield self.load_item_with_metadata(loader.load_item())
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))
