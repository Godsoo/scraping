from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re

from product_spiders.spiders.lego_cz.legobase import LegoMetadataBaseSpider


class Hracky4kidsSpider(LegoMetadataBaseSpider):
    name = u'hracky-4kids.cz'
    allowed_domains = ['www.hracky-4kids.cz']
    start_urls = [
        u'http://www.hracky-4kids.cz/stavebnice-lego/',
    ]
    errors = []

    def start_requests(self):
        set_currency_url = 'http://www.hracky-4kids.cz/inc/ajax/acurrency_change.php?money=1'
        yield Request(set_currency_url, callback=self.parse_currency)

    def parse_currency(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)        
        items = hxs.select('//div[@class="bordIn"]/a/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        items = hxs.select('//div[@id="products"]/div/h3/a/@href').extract()
        for url in items:
            yield Request(urljoin(base_url, url), callback=self.parse_product)
        if items:
            if not response.meta.get('url'):
                url = base_url
            else:
                url = response.meta['url']
            page = int(response.meta.get('n', 1))
            yield Request(urljoin(url, "strana-%d" % (page + 1)), callback=self.parse_category, meta={'url': url, 'n': page + 1})

    def parse_price(self, price):
        try:
            price, count = re.subn(r'[^0-9 .,]*([0-9 .,]+)\W*K.*', r'\1', price.strip())
        except TypeError:
            return False
        if count:
            price = price.replace(",", ".").replace(" ", "")
            try:
                price = float(price)
            except ValueError:
                return False
            else:
                return price
        elif price.isdigit():
            return float(price)
        return False

    def get_id(self, text):
        try:
            id, count = re.subn(r'[^0-9]*([0-9]+).*', r'\1', text)
        except TypeError:
            return False
        if count:
            id = id.strip()
            try:
                int(id)
            except ValueError:
                return False
            else:
                return id
        return False

    def parse_product(self, response):

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//div[@id="produktDET"]/div/div/h1[@class="or"]/text()').pop().extract().strip()

        category = hxs.select('//div[@id="link"]/a/@title').pop().extract().strip()

        sku = hxs.select('//span[@class="code"]/text()').extract().pop().strip()

        pid = self.get_id(hxs.select('//div[@class="buy"]/a/@href').pop().extract())

        price = hxs.select('//div[@class="pricebox"]/div/div/p[@class="prodCena"]/span/span[@class="actual_price"]/text()').pop().extract()

        stock = hxs.select('//div[@class="prodRight"]/div/div/p[@class="makeGreen"][contains(text(), "Skladem")]')

        if price:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('url', urljoin(base_url, response.url))
            loader.add_value('name', name)
            try:
                loader.add_xpath('image_url', '//div[@class="mainImgCont"]/a/img/@src', Compose(lambda v: urljoin(base_url, v[0])))
            except IndexError:
                self.errors.append("No image set for url: '%s'" % urljoin(base_url, response.url))
            loader.add_value('price', price.replace(' ', ''))
            loader.add_value('category', category)
            loader.add_value('sku', sku)
            loader.add_value('identifier', pid)
            loader.add_value('brand', 'LEGO')
            price = loader.get_output_value('price')
            if int(price) < 1990:
                loader.add_value('shipping_cost', 99)
            if not stock:
                loader.add_value('stock', 0)
            yield self.load_item_with_metadata(loader.load_item())
        else:
            self.errors.append("No price set for url: '%s'" % urljoin(base_url, response.url))
