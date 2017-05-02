import os
import re

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy import log

import csv, codecs, cStringIO

from productloader import load_product
from scrapy.http import FormRequest

HERE = os.path.abspath(os.path.dirname(__file__))
CSV_FILENAME = os.path.join(os.path.dirname(__file__), 'rvsupply.csv')

class rvsupplywarehouseDOSpider(BaseSpider):
    name = 'rvsupplywarehouse.com_DO'
    allowed_domains = ['www.rvsupplywarehouse.com', 'rvsupplywarehouse.com']
    start_urls = ('http://www.rvsupplywarehouse.com',
                  'http://www.rvsupplywarehouse.com/search?Q=%25%25%25&As=false&Cid=0&Isc=false&Mid=0&Pf=&Pt=&Sid=false',)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        categories = hxs.select('//div[contains(@class, "block-category-navigation")]//a/@href').extract()
        for url in categories:
            yield Request(urljoin_rfc(base_url, url))

        # pagination
        next_page = hxs.select(
                "//div[@class='pager']//li[@class='next-page']/a/@href"
                ).extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        # products
        products = hxs.select(
                "//div[@class='product-item']//h2[@class='product-title']"
                "/a/@href").extract()
        for product in products:
            product = urljoin_rfc(get_base_url(response), product)
            yield Request(product, callback=self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        res = {}
        hxs = HtmlXPathSelector(response)

        res['url'] = response.url
        name = hxs.select('//*[@itemprop="name"]//text()').extract()[0].strip()

        try:
            price = hxs.select('//*[@itemprop="price"]/span/text()').extract()[0]
        except:
            price = ""
        res['description'] = name
        res['price'] = price
        try:
            res['sku'] = hxs.select('//div[@class="manufacturer-part-number"]'
                                    '/span[@class="value"]/text()').extract()[0].strip()
        except:
            pass
        res['identifier'] = hxs.select('//div[@itemtype="http://schema.org/Product"]/@data-productid').extract()[0]
        image = hxs.select('//div[@class="picture"]//img/@src').extract()
        if image:
            res['image_url'] = urljoin_rfc(get_base_url(response), image[0].strip())
        try:
            res['category'] = hxs.select('//div[@class="breadcrumb"]/ul/li//a/span/text()')[-1].extract()
        except:
            pass
        try:
            res['brand'] = hxs.select('//div[@class="manufacturers"]/*[@class="value"]/*/text()').extract()[0]
        except:
            try:
                res['brand'] = hxs.select('//div[@class="manufacturers"]/*[@class="value"]/text()').extract()[0]
            except:
                pass
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
