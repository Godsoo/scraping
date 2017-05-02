import os
import csv
import codecs
import cStringIO
import logging

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class CampingWorldDOSpider(BaseSpider):
    name = 'campingworld.com_DO'
    allowed_domains = ['www.campingworld.com']
    start_urls = ('http://www.campingworld.com/search/index.cfm?Ntt=&N=0&Ntx=mode+matchallpartial&Ntk=primary&Nty=1&Ntpc=1&perPage=96',)

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        # get products
        products = hxs.select('//div[@id="srchcontain"]//div[@class="pic"]/a/@href').extract()
        if len(products) < 96:
            self.log('WARNING! Less than 96 products in page! => %s' % response.url)
        for product in products:
            yield Request(urljoin_rfc(base_url, product), callback=self.parse_product)

        # Next page
        next_page = hxs.select('//a[@rel="next"][1]/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        return



    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        options = hxs.select('//select[@id="skulist"]/option/@value').extract()
        if options:
            urls = hxs.select('//div[@class="leftcol"]//a/@href').extract()
            for url in urls:
                yield Request(urljoin_rfc(base_url, url), callback=self.parse_product)
        else:
            name = hxs.select('//div[@id="skuinfo"]/h1[@itemprop="name"]/text()').extract()
            if not name:
                name = hxs.select('//div[@class="details"]/h1/text()').extract()
            price = "".join(hxs.select('//div[@class="club"]/span[@itemprop="Price"]/text()').re(r'([0-9\,\. ]+)')).strip()
            if not price:
                price = "".join(hxs.select('//div[@class="details"]/div[@class="special"]/text()').re(r'([0-9\,\. ]+)')).strip()
            specs = hxs.select('//div[@id="specs"]/div[@class="special"]')
            specs += hxs.select('//p[@class="specs"]')
            model_no = None
            for spec in specs:
                spec_text = spec.select('./span[text()="Mfg Part #:"]').extract()
                if spec_text:
                    model_no = "".join(spec.select("./text()").extract()).strip()
            '''
            if not model_no:
                model_no = hxs.select("//meta[@itemprop='productID']/@content").extract()
            '''
            if not name:
                logging.error("NO NAME!!! %s" % response.url)
            if not price:
                logging.error("NO PRICE!!! %s" % response.url)
            if not model_no:
                logging.error("NO MODEL_NO!!! %s" % response.url)

            if name:
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('name', name[0])
                product_loader.add_value('sku', model_no)
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_xpath('image_url', '//meta[@itemprop="image"]/@content')
                product_loader.add_xpath('identifier', '//meta[@itemprop="productID"]/@content')

                categories = hxs.select('//div[@class="breadcrumb"]/a/text()')
                if categories:
                    product_loader.add_value('category', categories[-1].extract().strip())
                shipping = hxs.select('//span[@class="ship"]/text()')
                if shipping:
                    product_loader.add_value('shipping_cost', shipping[-1].extract().strip())
                brand = hxs.select('//p[@class="specs" and contains(span/text(), "Manufacturer")]/text()')
                if brand:
                    product_loader.add_value('brand', brand[-1].extract().strip())
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
