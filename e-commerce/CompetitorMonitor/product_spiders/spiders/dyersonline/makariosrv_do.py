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

class makariosrvDOSpider(BaseSpider):
    name = 'makariosrv.com_DO'
    allowed_domains = ['makariosrv.com']
    start_urls = ('http://makariosrv.com',)

    def __init__(self, *args, **kwargs):
        super(makariosrvDOSpider, self).__init__(*args, **kwargs)
        self._idents = []

    def start_requests(self):
        yield Request('http://www.makariosrv.com/', self.parse)

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//div[@id="SideCategoryList"]//a/@href').extract()
        for cat in cats:
            request = Request(urljoin_rfc(base_url, cat), callback=self.parse)
            yield request

        subcats = hxs.select('//div[@class="SubCategoryList"]//a/@href').extract()
        for cat in subcats:
            request = Request(urljoin_rfc(base_url, cat), callback=self.parse)
            yield request

        pages = hxs.select('//div[@class="CategoryPagination"]//a/@href').extract()
        for page in pages:
            request = Request(urljoin_rfc(base_url, page), callback=self.parse)
            yield request

        product_urls = hxs.select('//ul[contains(@class,"ProductList")]/li/div[contains(@class,"ProductImage")]/a/@href').extract()
        for product in product_urls:
            request = Request(product, callback=self.parse_product)
            yield request

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        res = {}

        url = response.url
        name = hxs.select('//div[@id="ProductDetails"]/h1/text()').extract()
        if name:
            price = "".join(hxs.select('//em[@class="ProductPrice VariationProductPrice"]/span[@class="SalePrice"]/text()').re(r'([0-9\,\. ]+)')).strip()
            if not price:
                price = "".join(hxs.select('//em[@class="ProductPrice VariationProductPrice"]/text()').re(r'([0-9\,\. ]+)')).strip()
            if not price:
                price = ''.join(hxs.select('//em[contains(@class, "ProductPrice")]/text()').re(r'([0-9\,\. ]+)')).strip()
            res['url'] = url
            res['description'] = name[0].strip()
            res['price'] = price
            res['identifier'] = hxs.select('//form/input[@name="product_id"]/@value')[0].extract()
            try:
                res['sku'] = hxs.select('//span[@class="VariationProductSKU"]/text()')[0].extract().strip()
            except:
                pass
            try:
                res['image_url'] = hxs.select('//div[@id="ProductDetails"]'
                                              '//div[@class="ProductThumbImage"]//img/@src')[0].extract()
            except:
                pass
            try:
                res['brand'] = hxs.select('//div[@class="Label" and contains(text(), "Brand")]'
                                          '/following-sibling::div[@class="Value"]/a/text()').extract()[0].strip()
            except:
                pass
            try:
                res['category'] = hxs.select('//div[@id="ProductBreadcrumb"]//li/a/text()').extract()[-1]
            except:
                pass
            try:
                stock = hxs.select('//span[@class="VariationProductInventory"]/text()').extract()[0].strip()
                if stock:
                    res['stock'] = stock
            except:
                pass
            if res['identifier'].strip() not in self._idents:
                self._idents.append(res['identifier'].strip())
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
