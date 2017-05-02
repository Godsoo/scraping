from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import TakeFirst, Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re


class WHSmithSpider(BaseSpider):
    name = u'legouk-whsmith.co.uk'
    allowed_domains = [u'whsmith.co.uk', u'www.whsmith.co.uk']
    start_urls = [u'http://www.whsmith.co.uk/dept/toys-and-games-toys-construction-toys-14x00008?filters=FILTER_brand%3aLEGO']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        links = hxs.select('//div[@class="product_info"]/a/h4/parent::a/@href').extract()
        for link in links:
            yield Request(urljoin(base_url, link), callback=self.parse_product)

        next_page = hxs.select('//ul[@class="pages"]//a/@href').extract()

        if next_page:
            link = next_page[0]
            yield Request(urljoin(base_url, link), callback=self.parse)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        name_xpath = '//div[@id="product-details"]/h1/span/text()'
        names = hxs.select('//h1[@id="product_title"]/text()').extract()

        if names and len(names) > 0:
            name = names[0].strip()
        else:
            # product not found. Just continue
            self.log('WARNING: Product not found => %s' % response.url)
            return

        quantity = hxs.select('//p[@id="stock_status"]/text()').extract()
        if quantity and "In Stock" in quantity.pop():
            quantity = None
        else:
            quantity = 0

        category = hxs.select('//ul[@id="crumbs"]/li[@class="last"]/a/text()').extract()

        brand = hxs.select('//div[@id="product_title_container"]/span[@class="secondary"]/text()').extract()

        loader = ProductLoader(response=response, item=Product())
        loader.add_value('url', urljoin(base_url, response.url))
        loader.add_value('name', name)
        loader.add_xpath('image_url', '//img[@id="main_image"]/@src', TakeFirst(), Compose(lambda v: urljoin(base_url, v)))
        loader.add_xpath('price', '//div[@class="product_price"]/span[@class="price"]/text()', TakeFirst(), re="([.0-9]+)")
        if not loader.get_output_value('price'):
            loader.add_value('price', 0)

        if category:
            loader.add_value('category', category[0].strip())

        loader.add_value('sku', name, TakeFirst(), re='(\d\d\d+)\s*$')

        if brand:
            loader.add_value('brand', brand[0].strip())

        identifier = hxs.select('//input[@name="ProductID"]/@value').extract()
        if not identifier:
            identifier = hxs.select('//li[@itemprop="id"]/text()').extract()
  
        loader.add_value('identifier', identifier[0])

        if quantity == 0:
            loader.add_value('stock', 0)

        yield loader.load_item()
