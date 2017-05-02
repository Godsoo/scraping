import os
import shutil
from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy.xlib.pydispatch import dispatcher

from lecreusetitems import LeCreusetMeta

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class MillysSpider(BaseSpider):
    name = 'lecreuset-millyskitchenstore.co.uk'
    allowed_domains = ['millyskitchenstore.co.uk']
    start_urls = ['http://www.millyskitchenstore.co.uk/LeCreuset-Category-3751.html']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="section"]//a/@href').extract():
            if '-Category-' in url:
                yield Request(urljoin_rfc(get_base_url(response), url))
            elif '-Product-' in url:
                yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//h1/span/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', 'Le Creuset')
        loader.add_xpath('category', '//ul[@class="breadcrumbs"]/li[position()>1]//span[@itemprop="title"]/text()')
        loader.add_xpath('sku', '//input[@name="productID"]/@value')
        loader.add_xpath('identifier', '//input[@name="productID"]/@value')
        image_url = hxs.select('//div[@id="thumbnails"]/a/img/@src').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        loader.add_xpath('price', '//div[@id="price"]/text()')
        if loader.get_output_value('price') < 25:
            loader.add_value('shipping_cost', '2.99')
        else:
            loader.add_value('shipping_cost', '0')

        if hxs.select('//a[@id="addcartlink"]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        item = loader.load_item()
        metadata = LeCreusetMeta()
        promotion = hxs.select('//img[contains(@src,"percent/sale_")]/@src').re('\d+')
        if promotion:
            metadata['promotion'] = promotion[0] + '% off retail price'
        item['metadata'] = metadata

        yield item

        
