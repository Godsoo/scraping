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

class rvwholesalersDOSpider(BaseSpider):
    name = 'rvwholesalers.com_DO'
    allowed_domains = ['www.rvwholesalers.com', 'rvwholesalers.com']
    start_urls = ('http://rvwholesalers.com/catalog/',)

    def parse(self, response):
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        cats = hxs.select('//div[@id="my_menu"]//a/@href').extract()
        for cat in cats:
            request = Request(urljoin_rfc(base_url, cat), callback=self.parse)
            yield request

        subcats = hxs.select('//td[@class="SubcatTitle"]/a/@href').extract()
        for scat in subcats:
            request = Request(urljoin_rfc(base_url, scat), callback=self.parse)
            yield request

        pages = hxs.select('//td[@class="NavigationCell"]/a/@href').extract()
        for page in pages:
            request = Request(urljoin_rfc(base_url, page), callback=self.parse)
            yield request

        products = hxs.select('//td[@class="PListCell"]')
        for product in products:
            name = product.select("./a[@class='ProductTitle']/text()").extract()
            if name:
                url = product.select("./a[@class='ProductTitle']/@href").extract()
                yield Request(urljoin_rfc(base_url, url[0]), self.parse_product)

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)
        res = {}

        products = hxs.select('//td[@class="PListCell"]')
        res['url'] = response.url
        res['description'] = hxs.select('//font[@class="NavigationPath"]'
                                        '[last()]/text()')[0].extract().strip()
        res['price'] = hxs.select('//span[@id="product_price"]/text()')[0].extract()
        sku = hxs.select('//td[@id="product_code"]/b/text()')[0].extract()
        mnf_number = re.findall(r'Manufacturer Part # ([\w-]+)', response.body)
        if not mnf_number:
            mnf_number = re.findall(r'Manufacturer # ([\w-]+)', response.body)
        if not mnf_number:
            mnf_number = re.findall(r'Part Number: ([\w-]+)', response.body)
        if not mnf_number:
            mnf_number = re.findall(r'manufactures # ([\w-]+)', response.body)
        if not mnf_number:
            mnf_number = re.findall(r'manufacture # ([\w-]+)', response.body)
        if not mnf_number:
            mnf_number = re.findall(r'Reese Part # ([\w-]+)', response.body)
        if mnf_number:
            res['sku'] = re.sub('<[^<]+?>', '', mnf_number[0].strip())
        else:
            res['sku'] = sku
        res['identifier'] = hxs.select('//form//input[@name="productid"]/@value')[0].extract()
        try:
            res['image_url'] = hxs.select('//img[@id="product_thumbnail"]/@src')[0].extract()
        except:
            pass
        try:
            res['category'] = hxs.select('//a[@class="NavigationPath"]/text()')[-1].extract()
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
