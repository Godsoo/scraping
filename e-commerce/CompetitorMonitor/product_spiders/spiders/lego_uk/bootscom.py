from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import TakeFirst
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re


class BootsSpider(BaseSpider):
    name = u'legouk-boots.com'
    allowed_domains = [u'www.boots.com']
    start_urls = [u'http://www.boots.com/en/LEGO/']

    def _start_requests(self):
        yield Request('http://www.boots.com/en/LEGO-Disney-Princess-Ariels-Treasure-41050_1492544/',
                callback=self.parse_product)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        anchors = hxs.select('//div[@class="narrowResults"]/div/ul/li[position()>1]/a')
        for anchor in anchors:
            url = anchor.select('@href').extract().pop()
            cat = anchor.select('text()').extract().pop().strip()
            yield Request(urljoin(base_url, url),
                          callback=self.parse_category,
                          meta={"category": cat})

    def parse_category(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        products = hxs.select('//a[@class="productName"]/@href').extract()
        for url in products:
            yield Request(urljoin(base_url, url),
                          callback=self.parse_product,
                          meta={"category": response.meta['category']})

        pages = hxs.select('//li[@class="paginationTop"]//a/@href').extract()
        for url in pages:
            yield Request(urljoin(base_url, url),
                          callback=self.parse_category,
                          meta={"category": response.meta['category']})

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name = hxs.select('//span[@itemprop="name"]/text()').extract().pop().strip()

        quantity = hxs.select('//*[@id="cpQuantity"]')
        if quantity:
            stock = True
        else:
            stock = False

        # cat_regex = 'LEGO Duplo|LEGO Bricks and More|LEGO Bricks|LEGO Creator|LEGO City|LEGO Ninjago|LEGO Monster Fighters|LEGO Super Heros|LEGO Lord Of The Rings|LEGO Star Wars|LEGO Games'

        try:
            identifier = hxs.select('//form[@name="TMS"]/input[@type="hidden" and @name="productId"]/@value').extract()[0]
        except:
            identifier = re.search(r'_(\d+)/', response.url).groups()[0]

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', urljoin(base_url, response.url))
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//meta[@property="og:image"]/@content')
        loader.add_xpath('price', '//p[@class="productOfferPrice"]/text()[1]', TakeFirst(), re="([.0-9]+)")
        loader.add_value('category', response.meta.get('category'))
        loader.add_value('sku', name, re=' (\d\d\d+)\s*$')
        loader.add_value('brand', "LEGO")
        loader.add_value('identifier', identifier)

        if not quantity:
            loader.add_value('stock', 0)

        yield loader.load_item()
