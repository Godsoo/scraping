# -*- coding: utf-8 -*-
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.items import Product, ProductLoader
from product_spiders.utils import extract_price_eu
import re


class Options(object):
    def __init__(self):
        self.data = {}

    def gen(self, items=None):
        if items is None:
            items = []
        # Generator returns [("opt1", (1, "title1")), ("opt2", (2, "title2"))]    [("opt1", (1, "title1")), ("opt2", (3, "title3"))]
        index = len(items)
        if not len(self.data):
            return
        if index >= len(self.data):
            yield items
            return
        option_name, options = self.data.items()[index]
        for name, val in options.items():
            for item in self.gen(items + [(option_name, (name, val))]):
                yield item

    def add_inputs(self, inputs, name_xpath=""):
        if not isinstance(inputs, list) and not isinstance(inputs, tuple):
            inputs = [inputs]
        for input in inputs:
            name = input.select('@name').extract()[0]
            if name not in self.data:
                self.data[name] = {}
            value = input.select('@value').extract()[0]
            title = "".join(input.select(name_xpath).extract()).strip() if name_xpath else ""
            self.data[name][value] = title
        return self

    def add_selects(self, selects):
        if not isinstance(selects, list) and not isinstance(selects, tuple):
            selects = [selects]
        for select in selects:
            name = select.select("@name").extract()[0]
            self.data[name] = {}
            for option in select.select('option'):
                title = option.select("text()").extract()[0]
                value = option.select("@value").extract()[0]
                if value:
                    self.data[name][value] = title
        return self


class ForstundagrartechnikSpider(BaseSpider):
    name = u'forstundagrartechnik.com'
    allowed_domains = ['www.forstundagrartechnik.com']
    start_urls = [
        u'http://www.forstundagrartechnik.com/',
    ]

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        categories = hxs.select('//ul[@id="categorymenu"]/li/a/@href').extract()
        for category in categories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)


    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        subcategories = hxs.select('//strong[contains(text(), "More sub catagories")]/following-sibling::table/tr/td//a/@href').extract()

        for category in subcategories:
            yield Request(urljoin_rfc(base_url, category), callback=self.parse_category)

        products = hxs.select('//div[contains(@class, "prod_wrapper")]/p[contains(@class, "prod_title")]/a/@href').extract()
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next_pages = hxs.select('//a[@class="pageResults"]/@href').extract()
        for page in next_pages:
            yield Request(urljoin_rfc(base_url, page), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//a[@class="headerNavigation"]/text()').extract()[2:-1]
        name = hxs.select('//h1/text()').extract()[0].strip()
        image_url = hxs.select('//img[@class="productimage"]/@src').extract()
        brand = hxs.select('//h2[contains(text(), "Manufacturer information") or contains(text(), "Hersteller Info")]/following-sibling::div[1]/center/strong/text()').extract() or [""]
        price = hxs.select('//p[@class="productprice"]//strong/text()').extract()
        sku = re.search("MPN: ([0-9]+)", response.body).group(1) if re.search("MPN: ([0-9]+)", response.body) else ""
        identifier = hxs.select('//input[@name="products_id"]/@value').extract()[0].strip()

        if not price:
            return

        price = extract_price_eu(price[0])

        for option in Options().add_inputs(hxs.select('//input[contains(@name, "id[")]'), name_xpath="following-sibling::text()[1]").gen():
            option = sorted(option)
            loader = ProductLoader(item=response.meta.get('product', Product()), selector=hxs)
            loader.add_value('url', response.url)
            loader.add_value('name', "%s %s" % (name, " ".join([x[1][1].strip() for x in option])))
            loader.add_value('brand', brand[0])
            if image_url:
                loader.add_value('image_url', urljoin_rfc(base_url, image_url[0]))
            for category in categories:
                loader.add_value('category', category)
            loader.add_value('price', price)
            loader.add_value('stock', 1)
            loader.add_value('sku', sku)
            loader.add_value('identifier', "%s-%s" % (identifier.strip(), "-".join([x[1][0] for x in option])))
            yield loader.load_item()
