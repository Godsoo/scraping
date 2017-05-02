import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc

import csv, codecs, cStringIO

from product_spiders.items import Product, ProductLoader

from utils import extract_price
from decimal import Decimal

HERE = os.path.abspath(os.path.dirname(__file__))

class AdventureRVDOSpider(BaseSpider):
    name = 'adventurerv.net_DO'
    allowed_domains = ['www.adventurerv.net']
    start_urls = ('http://www.adventurerv.net/advanced_search_result.php?keywords=%25',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        pages = hxs.select('//a[@title=" Next Page "]/@href').extract()
        for page in pages:
            request = Request(urljoin_rfc(base_url, page), callback=self.parse)
            yield request

        products = hxs.select('//div[@class="product-listing-text"]/a/@href').extract()
        for product in products:
            request = Request(urljoin_rfc(base_url, product), callback=self.parse_product)
            yield request

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        price = hxs.select('//div[@class="h3"]/span[@class="productSpecialPrice"]/text()')
        if not price:
            price = hxs.select('//div[@class="h3"]/text()')

        if price:
            name = hxs.select('//div[@id="content"]/div[@id="right-column"]/h1[@class="bottom-border"]/text()').extract()[0]
            price = hxs.select('//div[@class="h3"]/span[@class="productSpecialPrice"]/text()').extract()
            if not price:
                price = hxs.select('//div[@class="h3"]/text()').extract()
            image = hxs.select('//div[@id="right-column"]//a/img/@src')
            category = hxs.select('//div[@id="menu"]/child::div[last()]/a/text()')
            options = hxs.select('//form/select/option')
            if options:
                try:
                    mnfn = hxs.select('//div[contains(text(), "Manufacturer\'s Number")]'
                                      '/text()').re(r'Number: (.*)$')[0].strip()
                except:
                    mnfn = ''
                for option in options:
                    option_text = option.select('text()').extract()
                    if 'Please Choose' in option_text:
                        continue
                    sku = option.select('text()').re(r'#(\w+)')
                    if sku:
                        sku = sku[0]
                    else:
                        sku = option.select('text()').re(r'^([\w\'-/._]+)')[0]
                    product_loader = ProductLoader(item=Product(), response=response)
                    product_loader.add_value('name', name)
                    sum_price = option.select('text()').re(r' \(\+\$([\d.]+)')
                    if sum_price:
                        sum_ = Decimal(sum_price[0])
                    else:
                        sum_ = Decimal(0)
                    product_loader.add_value('price', extract_price(price[0]) + sum_)
                    product_loader.add_value('url', response.url)
                    product_loader.add_value('sku', mnfn)
                    ident = hxs.select('//form/input[@name="products_id"]/@value').extract()[0]
                    product_loader.add_value('identifier', '%s_%s' % (sku, ident))
                    if image:
                        product_loader.add_value('image_url', image[0].extract())
                    if len(category) > 1:
                        product_loader.add_value('category', category[-2].extract())
                    yield product_loader.load_item()
            else:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', name)
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                if image:
                    product_loader.add_value('image_url', image[0].extract())
                if len(category) > 1:
                    product_loader.add_value('category', category[-2].extract())
                try:
                    sku = hxs.select('//div[contains(text(), "Manufacturer\'s Number")]'
                                     '/text()').re(r'Number: (.*)$')[0].strip()
                except:
                    sku = ''
                product_loader.add_value('sku', sku)
                ident = hxs.select('//form/input[@name="products_id"]/@value').extract()[0]
                product_loader.add_value('identifier', '%s_%s' % (sku, ident))
                yield product_loader.load_item()



class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
