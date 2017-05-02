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

class KitchencookshopSpider(BaseSpider):
    name = 'lecreuset-kitchenscookshop.co.uk'
    allowed_domains = ['kitchenscookshop.co.uk']
    start_urls = ['http://store.kitchenscookshop.co.uk/catalogsearch/result/?q=Le+Creuset']

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//a[@class="product-image"]/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url), callback=self.parse_product)
        for url in hxs.select('//div[@class="pages"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url))

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//div[@class="product-name"]/h1/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', 'Le Creuset')
        loader.add_value('category', 'Le Creuset')
        loader.add_xpath('sku', '//input[@name="product"]/@value')
        loader.add_xpath('identifier', '//input[@name="product"]/@value')
        image_url = hxs.select('//div[@class="product-img-box"]/a/@href').extract()
        if image_url:
            loader.add_value('image_url', image_url[0])
        loader.add_xpath('price', '//div[@class="prodPriceWrap"]/h2/text()')
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', '4.75')
        else:
            loader.add_value('shipping_cost', '0')

        loader.add_value('stock', '1')

        item = loader.load_item()
        metadata = LeCreusetMeta()
        item['metadata'] = metadata

        yield item

        
