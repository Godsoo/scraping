import re
import os
import csv
import shutil
from decimal import Decimal
from cStringIO import StringIO

from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.item import Item, Field

from product_spiders.items import (
    Product,
    ProductLoaderWithNameStrip as ProductLoader,
)

from scrapy.http import Request, HtmlResponse


HERE = os.path.abspath(os.path.dirname(__file__))

class LakelandMeta(Item):
    promotion = Field()


class LakelandSpider(BaseSpider):
    name = 'le_creuset-lakeland.co.uk'
    allowed_domains = ['lakeland.co.uk']
    start_urls = ('http://www.lakeland.co.uk/brands/le-creuset?intcmp=INTSRCH:lecreuset',)


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        next_page = hxs.select('//a[@class="next-page"]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products = hxs.select('//div[@class="section product-and-category-list"]//dl[@class="hproduct"]/dt/a/@href').extract()
        for url in products:
            yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)


    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        loader = ProductLoader(item=Product(), response=response)
        identifier = re.search('uk/(p?\d+)/', response.url).group(1)
        loader.add_value('identifier', identifier)
        sku = hxs.select('//span[@class="identifier"]/span[@class="value"]/text()').extract()[0].strip()
        loader.add_value('sku', sku)
        name = hxs.select('//h1[@class="fn"]/text()').extract()[0].strip()
        loader.add_value('name', name)
        loader.add_value('category', 'Le Creuset')
        loader.add_xpath('image_url', '//div[@class="slide photo"]/a/img[contains(@class, "photo")]/@src')
        loader.add_value('brand', 'Le Creuset')
        loader.add_value('url', response.url)
        
        price = hxs.select('//dd[@class="price now"]/text()').extract()
        if not price:
            price = hxs.select('//p[@class="price"]/text()').extract()
        
        price = price[0].strip() if price else 0
        loader.add_value('price', price)
        stock = hxs.select('//p[@class="stock-notice" and contains(text(), "In Stock")]')
        if not stock:
            loader.add_value('stock', 0)
        price = loader.get_output_value('price')
        if price:
            price = Decimal(price)
            if price < 30.0:
                loader.add_value('shipping_cost', '2.99')
        metadata = LakelandMeta()
        promotion = ' '.join(hxs.select('//div[@class="section promotion special-offer"]/text()').extract())
        if promotion:
            promotion = re.sub('[ \n\r]', ' ', promotion)
            promotion = re.sub(' +', ' ', promotion).strip()
            metadata['promotion'] = promotion
        product = loader.load_item()
        product['metadata'] = metadata
        yield product
