import re
import os

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse
from scrapy.utils.url import urljoin_rfc
from scrapy.utils.response import get_base_url
from scrapy import log

import csv, codecs, cStringIO

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

class PplmotorhomesDOSpider(BaseSpider):
    USER_AGENT = "Googlebot/2.1 ( http://www.google.com/bot.html)"
    name = 'pplmotorhomes.com_DO'
    allowed_domains = ['www.pplmotorhomes.com', 'pplmotorhomes.com']
    start_urls = ('http://www.pplmotorhomes.com/parts/rv_parts_rv_accessories.htm',
                  'http://www.pplmotorhomes.com/parts/towing')

    _products = {}

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return

        hxs = HtmlXPathSelector(response)
        base_url = get_base_url(response)

        cats = hxs.select('//div[@class="mC"]//a/@href').extract()
        cats += hxs.select('//div[@id="tabbed_nav"]//a/@href').extract()
        for cat_url in cats:
            yield Request(urljoin_rfc(base_url, cat_url))

        next_page = hxs.select('//li[@class="next_page"][1]/a/@href').extract()
        if next_page:
            yield Request(urljoin_rfc(base_url, next_page[0]))

        products_url = [url for url in hxs.select('//table//a/@href').extract()
                        if not url.startswith('#')]
        products_url += hxs.select('//div[@id="prod_use_cont"]//a/@href').extract()
        for url in products_url:
            yield Request(urljoin_rfc(base_url, url))

        # Parse products
        products = hxs.select('//table[@width="86%"]/tr')
        for product in products:
            stock_number = product.select('./form/td[1]/b/text()').extract()
            sku = ''.join(product.select('.//font[contains(text(), "Manufacturer #")]/b/text()').extract())
            price = "".join(product.select("./form/td[3]/font/b/text()").re(r'([0-9\,\. ]+)')).strip()
            if stock_number and price:
                stock_number = stock_number[0].strip()
                if stock_number in self._products:
                    name = self._products[stock_number]  # Will be filtered then by DuplicateProductPickerPipeline taking lowest price
                else:
                    name = product.select('./form/td[2]/text()').extract()[0].strip()
                    if '...Regularly' in name:
                        name = re.sub('\.{3}Regularly.*?\$.*$', '', name)
                    self._products[stock_number] = name
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('sku', sku)
                product_loader.add_value('identifier', stock_number)
                product_loader.add_value('name', name)
                category = hxs.select('//div[@id="breadcrumbs"]//a/text()')
                if category:
                    product_loader.add_value('category', category[-1].extract())
                image = hxs.select('//div[@id="title"]/following-sibling::*//img/@src')
                if image:
                    product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), image[0].extract()))
                yield product_loader.load_item()
        name = hxs.select(u'//h1[@class="big product_title"]/text()').extract()
        if not products and name:
            product_loader = ProductLoader(item=Product(), response=response)
            name = name[0]
            if '...Regularly' in name:
                name = re.sub('\.{3}Regularly.*?\$.*$', '', name)
            try:
                identifier = hxs.select(u'//strong[@id="pplno"]/text()').extract()[0].strip()
            except:
                identifier = hxs.select(u'//span[contains(text(), "PPL Part #")]'
                                        '/following-sibling::*[1]/text()').extract()[0].strip()
            product_loader.add_value('name', name)
            product_loader.add_xpath('price', u'//dt[@id="prod_price"]//span[@class="small"]/strong[@class="big"]/text()',
                                    re='\$(.*)')
            product_loader.add_xpath('sku', u'//span[contains(text(), "Manufacturer #")]/following-sibling::*[1]/text()')
            product_loader.add_value('identifier', identifier)
            product_loader.add_xpath('image_url', u'//img[@id="prod_img"]/@src')
            product_loader.add_value('url', response.url)
            category = hxs.select('//div[@id="crumb"]//a/text()')
            if category:
                product_loader.add_value('category', category[-1].extract())
            yield product_loader.load_item()

    '''
    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        hxs = HtmlXPathSelector(response)
        products = hxs.select('//table[@width="86%"]/tr')
        for product in products:
            sku = product.select('./form/td[1]/b/text()').extract()
            price = "".join(product.select("./form/td[3]/font/b/text()").re(r'([0-9\,\. ]+)')).strip()
            if sku and price:
                name = product.select('./form/td[2]/text()').extract()[0]
                if '...Regularly' in name:
                    name = re.sub('\.{3}Regularly.*?\$.*$', '', name)
                product_loader = ProductLoader(item=Product(), response=response)
                product_loader.add_value('price', price)
                product_loader.add_value('url', response.url)
                product_loader.add_value('sku', sku)
                product_loader.add_value('identifier', sku)
                product_loader.add_value('name', name)
                category = hxs.select('//div[@id="breadcrumbs"]//a/text()')
                if category:
                    product_loader.add_value('category', category[-1].extract())
                image = hxs.select('//div[@id="title"]/following-sibling::*//img/@src')
                if image:
                    product_loader.add_value('image_url', urljoin_rfc(get_base_url(response), image[0].extract()))
                yield product_loader.load_item()
        name = hxs.select(u'//h1[@class="big product_title"]/text()').extract()
        if not products and name:
            product_loader = ProductLoader(item=Product(), response=response)
            name = name[0]
            if '...Regularly' in name:
                name = re.sub('\.{3}Regularly.*?\$.*$', '', name)
            try:
                identifier = hxs.select(u'//strong[@id="pplno"]/text()').extract()[0].strip()
            except:
                identifier = hxs.select(u'//span[contains(text(), "PPL Part #")]'
                                        '/following-sibling::*[1]/text()').extract()[0].strip()
            product_loader.add_value('name', name)
            product_loader.add_xpath('price', u'//dt[@id="prod_price"]//span[@class="small"]/strong[@class="big"]/text()',
                                    re='\$(.*)')
            product_loader.add_xpath('sku', u'//span[contains(text(), "Manufacturer #")]/following-sibling::*[1]/text()')
            product_loader.add_value('identifier', identifier)
            product_loader.add_xpath('image_url', u'//img[@id="prod_img"]/@src')
            product_loader.add_value('url', response.url)
            category = hxs.select('//div[@id="crumb"]//a/text()')
            if category:
                product_loader.add_value('category', category[-1].extract())
            yield product_loader.load_item()
    '''

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
