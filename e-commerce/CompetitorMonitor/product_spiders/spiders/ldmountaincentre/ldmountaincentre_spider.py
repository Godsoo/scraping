import os
import shutil

from lxml import etree

from scrapy import signals
from scrapy import log
from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.xlib.pydispatch import dispatcher


from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class LdMountainCentreSpider(BaseSpider):
    name = 'ldmountaincentre.com'
    allowed_domains = ['ldmountaincentre.com']

    def __init__(self, *a, **kw):
        super(LdMountainCentreSpider, self).__init__(*a, **kw)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        if spider.name == self.name:
            shutil.copy('data/%s_products.csv' % spider.crawl_id, os.path.join(HERE, 'product_skus.csv'))
            log.msg("CSV is copied")

    def start_requests(self):
        with open(os.path.join(HERE, 'ldmountaincentre.xml')) as f:
            root = etree.fromstring(f.read())
            for item in root.xpath('//item'):
                meta = {}
                sku = ''
                size = ''
                color = ''
                if item.xpath('gtin'):
                    sku = item.xpath('gtin')[0].text

                meta['sku'] = sku
                meta['image_url'] = item.xpath('image_link')[0].text
                meta['identifier'] = item.xpath('id')[0].text
                meta['name'] = item.xpath('title')[0].text
                meta['brand'] = item.xpath('brand')[0].text
                if item.xpath('size'):
                    size = item.xpath('size')[0].text
                meta['size'] = size
                if item.xpath('color'):
                    color = item.xpath('color')[0].text
                meta['color'] = color
                meta['category'] = item.xpath('google_product_category')[0].text.split('>')[-1]
                meta['url'] = item.xpath('link')[0].text

                yield Request(meta['url'], meta=meta)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        meta = response.meta
        loader = ProductLoader(item=Product(), response=response)
        loader.add_value('sku', meta['sku'])
        loader.add_value('identifier', meta['identifier'])

        name = meta['name']
        if meta['color']:
            name = name + ' - ' + meta['color']
        if meta['size']:
            name = name + ' - ' + meta['size']

        loader.add_value('name', name)
        loader.add_value('url', response.url)
        loader.add_value('brand', meta['brand'])
        loader.add_value('category', meta['category'])
        loader.add_value('image_url', meta['image_url'])
        price = hxs.select('//div[@id="product_price"]/div/span[not(@id="product_price_was")]/span[@class="price"]/span[@class="inc"]/span[@class="GBP"]/text()').extract()
        if not price:
            price = hxs.select('//div[@id="product_price_sale_holder"]/span/span/span/span[@class="inc"]/span[@class="GBP"]/text()').extract()
        if not price:
            price = hxs.select('//span[@id="product_price_sale"]//span[@class="GBP" and @itemprop="price"]/text()').extract()
        loader.add_value('price', price[0] if price else 0)
        yield loader.load_item()
