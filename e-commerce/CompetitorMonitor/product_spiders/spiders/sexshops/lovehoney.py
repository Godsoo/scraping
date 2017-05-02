import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc, canonicalize_url

from product_spiders.items import Product, ProductLoaderWithoutSpaces as ProductLoader

from productloader import load_product

from scrapy import log


class LoveHoney(BaseSpider):
    name = 'lovehoney.co.uk'
    allowed_domains = ['lovehoney.co.uk']
    start_urls = ('http://www.lovehoney.co.uk',)

    def __init__(self, *args, **kwargs):
        super(LoveHoney, self).__init__(*args, **kwargs)
        self.URL_BASE = 'http://www.lovehoney.co.uk'

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        if response.url == self.URL_BASE:
            cats = hxs.select('//li[not (@id="tabCommunity") and not(@id="tabHelp")]/ul[@class="flyout"]//a/@href').extract()
            for cat in cats:
                yield Request(
                    url=canonicalize_url(urljoin_rfc(self.URL_BASE, cat)),
                    callback=self.parse_cat)

    def parse_cat(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)

        products = hxs.select('//div[@class="bd"]/ol/li/ul/li/h4/a/@href').extract()

        next_page = hxs.select('//div[@class="pagenav"]/a[@class="next"]/@href').extract()
        if next_page:
            yield Request(
                url=canonicalize_url(urljoin_rfc(self.URL_BASE, next_page[0])),
                callback=self.parse_cat)

        products = hxs.select('//div[@class="bd"]/ol/li/ul/li/h4/a/@href').extract()

        for product in products:
            url = urljoin_rfc(get_base_url(response), product)
            yield Request(url, callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        name = hxs.select('//li[@class="details"]//h1/text()').extract()[0]
        url = response.url
        price = hxs.select(
            '//li[@class="details"]//p[contains(@class, "our-price")]'
            '/strong/text()').re('\xa3(.*)')[0]
        identifier = response.url.split('p=')[-1]

        loader = ProductLoader(item=Product(), selector=hxs)
        loader.add_value('url', url)
        loader.add_value('name', name)
        loader.add_value('price', price)
        loader.add_value('identifier', identifier)
        sku = hxs.select('//form[@id="productForm"]/p/input[@name="p"]/@value').extract()
        if sku:
            loader.add_value('sku', sku[-1])

        # loader.add_value('brand', response.meta['brand'])
        category = hxs.select('//ol[@class="breadcrumbs"]/li/a/text()').extract()
        if category:
            loader.add_value('category', category[-1])
        stock = hxs.select('//span[@class="prod-instock"]/text()').extract()
        if not stock:
            loader.add_value('stock', 0)
        image_url = hxs.select('//img[@id="productImage"]/@src').extract()
        if image_url:
            loader.add_value('image_url', 'http:' + image_url[0])
        yield loader.load_item()
