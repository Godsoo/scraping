import os
import csv

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.utils.response import get_base_url
from scrapy.contrib.loader.processor import TakeFirst, Compose
from urlparse import urljoin
from product_spiders.items import Product, ProductLoader
import re

from urllib2 import urlopen, URLError

from scrapy import log

from bookpeoplemeta import BookpeopleMeta

HERE = os.path.abspath(os.path.dirname(__file__))

class WHSmithSpider(BaseSpider):
    name = u'thebookpeople-whsmith.co.uk'
    allowed_domains = [u'whsmith.co.uk', u'www.whsmith.co.uk']
    start_urls = [u'http://www.whsmith.co.uk']

    def start_requests(self):
        with open(os.path.join(HERE, 'thebookpeople.co.uk_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                search_url = 'http://www.whsmith.co.uk/pws/ProductDetails.ice?ProductID=%s'
                url = search_url % row['sku']
                url = urlopen(url).geturl()
                if 'ProductDetails' in url:
                    yield Request(url, dont_filter=True)

    def parse(self, response):
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
        if quantity and 'OUT OF STOCK' in quantity.pop().upper():
            quantity = 0
        else:
            quantity = None

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

        sku = hxs.select('//li[@itemprop="ISBN13"]/text()').extract()
        sku = sku[-1].strip() if sku else ''
        loader.add_value('sku', sku)

        if brand:
            loader.add_value('brand', brand[0].strip())

        identifier = hxs.select('//input[@name="ProductID"]/@value').extract()
        if not identifier:
            identifier = hxs.select('//li[@itemprop="id"]/text()').extract()
  
        loader.add_value('identifier', identifier[0])

        if quantity == 0:
            loader.add_value('stock', 0)

        item = loader.load_item()

        metadata = BookpeopleMeta()
        pre_order = hxs.select('//button[contains(@class, "submit") and text()="Pre order"]')
        metadata['pre_order'] = 'Yes' if pre_order else ''
        author = hxs.select('//span[contains(em/text(), "author")]/a/text()').extract()
        metadata['author'] = author[0] if author else ''
        book_format = hxs.select('//li[@itemprop="Format"]/text()').extract()
        metadata['format'] = book_format[-1].strip() if book_format else ''
        publisher = hxs.select('//span[@itemprop="publisher"]/a/text()').re(': (.*)')
        metadata['publisher'] = publisher[0] if publisher else ''
        published = hxs.select('//li[@itemprop="publication date"]/text()').extract()
        metadata['published'] = published[-1].strip() if published else ''
        item['metadata'] = metadata
        yield item
