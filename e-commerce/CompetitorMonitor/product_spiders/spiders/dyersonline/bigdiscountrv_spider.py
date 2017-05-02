import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

import csv, codecs, cStringIO

from productloader import load_product
from scrapy.http import FormRequest

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class bigdiscountrvDOSpider(BaseSpider):
    name = 'bigdiscountrv.com_DO'
    allowed_domains = ['www.bigdiscountrv.com', 'bigdiscountrv.com']
    start_urls = ('http://bigdiscountrv.com/',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//div[@id="col1"]/ul/li/a/@href').extract()
        cats += hxs.select('//div[@id="col2"]/ul/li/a/@href').extract()
        cats += hxs.select('//div[@id="col3"]/ul/li/a/@href').extract()
        for cat in cats:
            request = Request(urljoin_rfc(base_url, cat), callback=self.parse)
            yield request

        scats = hxs.select('//ul[@class="catalogueList"]/li/div/h4/a/@href').extract()
        for scat in scats:
            request = Request(urljoin_rfc(base_url, scat), callback=self.parse)
            yield request

        product_urls = hxs.select('//td[@class="productItem"]/div/div/a/@href').extract()
        for product in product_urls:
            request = Request(urljoin_rfc(base_url, product), callback=self.parse_product)
            yield request

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        res = {}

        name = hxs.select("//div[@class='details']/h3/text()").extract()
        if name:
            url = response.url
            price = "".join(hxs.select('//li[@class="priceBigD"]'
                                       '/text()').re(r'([0-9\,\. ]+)')).strip()
            try:
                sku = hxs.select('//ul[@id="pricing"]/li[@class="priceStockNo"]'
                                 '/text()').re(r'No.:(.*)$')[0].strip()
            except:
                sku = ''
            image = hxs.select('//div[@class="image"]//img/@src')
            if image:
                res['image_url'] = urljoin_rfc(base_url, image[0].extract())
            category = hxs.select('//div[@class="breadcrumbs"]/a/text()')
            if category:
                res['category'] = category[-1].extract()
            res['identifier'] = hxs.select('//*[@id="addtocart"]/img/@onclick')\
                .re(r'AddToCart\(\d+,(\d+)')[0]
            if price:
                res['url'] = url
                res['description'] = name[0].strip()
                res['price'] = price
                res['sku'] = sku
                yield load_product(res, response)


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
