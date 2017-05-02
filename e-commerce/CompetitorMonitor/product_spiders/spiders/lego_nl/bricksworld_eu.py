from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from urlparse import urljoin as urljoin_rfc
from scrapy.utils.response import get_base_url
from product_spiders.utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from scrapy import log


class BricksWorldSpider(BaseSpider):
    name = 'bricksworld.eu'
    allowed_domains = ['bricksworldowncreations.com']
    start_urls = ['http://bricksworldowncreations.com/nl/']
    errors = []

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)
        for url in hxs.select('//*[@id="block_top_menu"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_category)

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        sub_categories = hxs.select('//a[@class="subcategory-name"]/@href').extract()
        for sub_category in sub_categories:
            yield Request(urljoin_rfc(base_url, sub_category), callback=self.parse_category)

        for product in hxs.select('//h5[@itemprop="name"]//a/@href').extract():
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        next = hxs.select('//li[@id="pagination_next"]/a/@href').extract()
        if next:
            yield Request(urljoin_rfc(base_url, next[0]), callback=self.parse_category)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        loader = ProductLoader(item=Product(), selector=hxs)
        identifier = hxs.select('//input[@name="id_product"]/@value').extract()[0]
        loader.add_value('identifier', identifier)
        sku = hxs.select('//span[@itemprop="sku"]/@content').extract()
        sku = sku[0].replace('LEGO', '') if sku else ''
        loader.add_value('sku', sku)
        loader.add_value('url', response.url)
        loader.add_xpath('name', '//h1[@itemprop="name"]/text()')
        price = ''.join(hxs.select('//p[@class="our_price_display"]/span[@class="price"]/text()').extract())
        price = extract_price(price)
        loader.add_value('price', price)
        img = hxs.select('//img[@id="bigpic"]/@src').extract()
        if img:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), img.pop()))
        category = hxs.select('//span[@class="navigation_page"]//a/span/text()').extract()
        category = category[0] if category else ''
        loader.add_value('category', category)
        loader.add_value('brand', 'Lego')
        yield loader.load_item()
