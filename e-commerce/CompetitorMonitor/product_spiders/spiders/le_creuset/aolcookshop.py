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

class AolcookshopSpider(BaseSpider):
    name = 'lecreuset-aolcookshop.co.uk'
    allowed_domains = ['aolcookshop.co.uk']
    start_urls = ['http://www.aolcookshop.co.uk/acatalog/Le_Creuset.html']

    def _start_requests(self):
#        yield Request('http://www.aolcookshop.co.uk/acatalog/Le-Creuset-Enamelled-Kone-Kettle-2.8pt-plus-two-FREE-Stoneware-Mugs-Volcanic--FR3317.html')
        yield Request('http://www.aolcookshop.co.uk/acatalog/Le-Creuset-Cast-Iron-Omelette-Pan-20cm-Nutmeg-36647.html')


    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        for url in hxs.select('//div[@class="product_list"]//a/@href').extract():
            yield Request(urljoin_rfc(get_base_url(response), url))

        if not hxs.select('//span[@class="product"]/h1/text()'):
            return

        loader = ProductLoader(item=Product(), response=response)
        loader.add_xpath('name', '//span[@class="product"]/h1/text()')
        loader.add_value('url', response.url)
        loader.add_value('brand', 'Le Creuset')
        loader.add_xpath('category', '//div[@class="text_breadcrumbs"]/a[position()>1]//text()')
        loader.add_xpath('sku', 'substring-after(//font[@size="1" and contains(text(), "Ref:")]/text(), ": ")')
        loader.add_xpath('identifier', 'substring-after(//font[@size="1" and contains(text(), "Ref:")]/text(), ": ")')
        image_url = hxs.select('//img[@class="fullimage1"]/@src').extract()
        if image_url:
            loader.add_value('image_url', urljoin_rfc(get_base_url(response), image_url[0]))
        loader.add_xpath('price', '//h3[@class="product_price"]/prices/span[2]/text()')
        if not loader.get_output_value('price'):
            loader.add_xpath('price', '//h3[@class="product_price"]//text()')
        if loader.get_output_value('price') < 50:
            loader.add_value('shipping_cost', '4.95')
        else:
            loader.add_value('shipping_cost', '0')

        if hxs.select('//div[@class="stock-message"]/span[contains(.//text(), "In stock") or contains(.//text(), "plenty of stock in")]'):
            loader.add_value('stock', '1')
        else:
            loader.add_value('stock', '0')

        item = loader.load_item()
        metadata = LeCreusetMeta()
        metadata['promotion'] = ''.join(hxs.select('//div[@class="special-offer-message"]/span/text()').extract())
        item['metadata'] = metadata

        yield item

        
