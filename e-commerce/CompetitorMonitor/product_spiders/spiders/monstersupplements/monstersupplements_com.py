import os
import re
import urllib
import shutil
from string import strip
from decimal import Decimal
from scrapy import signals
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.xlib.pydispatch import dispatcher
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

from utils import extract_price
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class MonstersupplementsComSpider(BaseSpider):
    name = 'monstersupplements.com'
    allowed_domains = ['monstersupplements.com']

    def __init__(self, *args, **kwargs):
        super(MonstersupplementsComSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'monstersupplements.csv'))

    def start_requests(self):
        yield Request('http://www.monstersupplements.com', callback=self.parse_full)

    def parse_full(self, response):
        hxs = HtmlXPathSelector(response)

        for url in hxs.select(u'//*[@class="top_menu"]//a/@href').extract():
            url = urljoin_rfc(get_base_url(response), url)
            yield Request(url, callback=self.parse_product_list, meta=response.meta)

    def parse_product_list(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta.copy()

        if not meta.has_key('category'):
            category = hxs.select('//div[@class="section_title"]/h1/text()').extract()
            if category:
                meta['category'] = category[0].strip()

        if not meta.has_key('brand'):
            brands_list = zip(map(strip,
                                  hxs.select('//div[@class="refine_title top_gap" '
                                             'and contains(text(), "Brand")]'
                                             '/following-sibling::div[@id="search_categories_refine"]'
                                             '/a/text()').extract()),
                              map(lambda url: urljoin_rfc(get_base_url(response), url),
                                  hxs.select('//div[@class="refine_title top_gap" '
                                             'and contains(text(), "Brand")]'
                                             '/following-sibling::div[@id="search_categories_refine"]'
                                             '/a/@href').extract()))

            for brand, url in brands_list:
                meta['brand'] = brand
                yield Request(url, callback=self.parse_product_list, meta=meta)
        else:
            for url in hxs.select(u'//a[contains(@id, "productlist_long_name")]/@href').extract():
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product, meta=meta)

            for url in hxs.select(u'//div/span[@class="pagenum"]/..//a/@href').extract():
                url = urljoin_rfc(get_base_url(response), url)
                yield Request(url, callback=self.parse_product_list, meta=meta)

    def get_options(self, hxs):
        names = hxs.select('//div[@id="product_options_holder_box"]//label/text()').extract()
        stock = ['out of stock' not in n.lower() for n in names]
        names = [name.split('[')[0].strip() for name in names if name]
        return zip(names, stock)

    def parse_product(self, response):
        hxs = HtmlXPathSelector(response)

        product_loader = ProductLoader(item=Product(), selector=hxs)
        product_loader.add_value('url', response.url)
        product_loader.add_xpath('name', u'//h1//text()')
        product_loader.add_value('category', response.meta.get('category', ''))
        product_loader.add_xpath('price', u'//span[@itemprop="price"]/text()')

        product_loader.add_xpath('sku', u'//input[@name="pid"]/@value')
        product_loader.add_xpath('identifier', u'//input[@name="pid"]/@value')
        product_loader.add_xpath('sku', u'//input[@name="product_ID"]/@value')
        product_loader.add_xpath('identifier', u'//input[@name="product_ID"]/@value')

        img = hxs.select(u'//div[@id="largepic"]//img/@data-zoom-image').extract()
        if img:
            product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), img[0]))


        product_loader.add_value('brand', response.meta['brand'])
        # product_loader.add_xpath('shipping_cost', '')

        if hxs.select('//div[@id="buybox"]//div[@class="warning_message" and contains(text(), "out of stock")]'):
            product_loader.add_value('stock', 0)

        product = product_loader.load_item()
        options = self.get_options(hxs)
        if options:
            for name, stock in options:
                prod = Product(product)
                prod['name'] = prod['name'] + ' ' + name
                prod['identifier'] = prod['sku'] + ':' + name.strip()\
                    .replace(' ', '').replace('/', '').replace('-', '').lower()
                if not stock:
                    prod['stock'] = 0
                yield prod
        else:
            yield product
