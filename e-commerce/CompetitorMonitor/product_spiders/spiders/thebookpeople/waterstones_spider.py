import os
import csv
import datetime

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.spider import BaseSpider
from scrapy import log

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from bookpeoplemeta import BookpeopleMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class WaterstonesSpider(BaseSpider):
    name = 'thebookpeople-waterstones.com'
    allowed_domains = ['waterstones.com']
    start_urls = ['http://www.waterstones.com']

    def start_requests(self):
        with open(os.path.join(HERE, 'thebookpeople.co.uk_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                search_url = 'https://www.waterstones.com/books/search/term/%s'
                yield Request(search_url % row['sku'])

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        identifier = hxs.select('//div[@class="button-container"]/input[@name="productid"]/@value').extract()
        if identifier:
            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('identifier', identifier[0])
            loader.add_xpath('name', '//div[@class="book-info"]/h1/span/text()')
            loader.add_xpath('price', '//b[@itemprop="price"]/text()')
            isbn = hxs.select('//span[@itemprop="isbn"]/text()').extract()
            if isbn:
                loader.add_value('sku', isbn[0])
            loader.add_value('url', response.url)
            categories = hxs.select('//div[contains(@class, "breadcrumbs")]/a/text()').extract()
            for category in categories:
                loader.add_value('category', category)
            if loader.get_output_value('price') < 10:
                loader.add_value('shipping_cost', 2.75)
            in_stock = 'IN STOCK' in ''.join(hxs.select('//ul[@class="perk-list"]/li/text()').extract()).upper()
            if not in_stock:
                loader.add_value('stock', 0)
            loader.add_xpath('image_url', '//img[@id="scope_book_image"]/@src')
            item = loader.load_item()
            metadata = BookpeopleMeta()
            pre_order = hxs.select('//button[@class="button button-teal button-buy"]/text()').extract()[0]
            if pre_order == 'Pre-order':
                metadata['pre_order'] = 'Yes'
            author = hxs.select('//span[@itemprop="author"]/text()').extract()
            if author:
                metadata['author'] = author[0]
            format_ = hxs.select('//div[@class="book-actions"]//span[@itemprop="bookFormat" and @class="name"]/text()').extract()
            if format_:
                metadata['format'] = format_[0].strip()
            publisher = hxs.select('//span[@itemprop="publisher"]/text()').extract()
            if publisher:
                metadata['publisher'] = publisher[0]
            published = hxs.select('//div[@class="book-actions"]//meta[@itemprop="datePublished"]/@content').extract()
            if published:
                metadata['published'] = datetime.datetime.strptime(published[0], "%Y-%m-%d").strftime('%d %B %Y')
            item['metadata'] = metadata
            yield item
        else:
            log.msg('NOT PRODUCT FOUND: ' + response.url)
