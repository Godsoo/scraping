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

class tweetysDOSpider(BaseSpider):
    name = 'tweetys.com_DO'
    allowed_domains = ['www.tweetys.com', 'tweetys.com']
    start_urls = ('http://www.tweetys.com/search.aspx?find=',)

    def __init__(self, *argv, **kwgs):
        super(tweetysDOSpider, self).__init__(*argv, **kwgs)
        self._idents = []

    def parse(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        product_urls = hxs.select('//div[@class="product-list-item"]/a/@href').extract()
        for product in product_urls:
            request = Request(urljoin_rfc(base_url, product), callback=self.parse_product)
            yield request

        pages = hxs.select('//a[@title="Go to the next page"]/@href').extract()
        for page in pages:
            request = Request(urljoin_rfc(base_url, page), callback=self.parse)
            yield request

    def parse_product(self, response):
        if not isinstance(response, HtmlResponse):
            return
        base_url = get_base_url(response)
        hxs = HtmlXPathSelector(response)

        try:
            sku = hxs.select('//*[@itemprop="mpn"]/text()').extract()[0].strip()
        except:
            self.log('NO SKU => %s' % (response.url,))
            sku = ''

        options = hxs.select("//select[contains(@name,'ddlVariationGroup')]/option")
        res = {}
        if not options or 'option' in response.meta:
            # no options
            name = hxs.select("//*[@itemprop='name']/text()")[0].extract().strip()
            if 'option' in response.meta:
                name += ' - %s' % (response.meta['option'].strip())
            url = response.url
            price = "".join(hxs.select('//span[@class="prod-detail-cost-value"]/text()').re(r'([0-9\,\. ]+)')).strip()
            image = hxs.select('//a[@id="Zoomer"]/img/@src')
            if image:
                res['image_url'] = urljoin_rfc(get_base_url(response), image[0].extract())
            category = hxs.select('//div[@class="breadcrumb"]/span/span/a/text()')
            if category:
                res['category'] = category[-1].extract().strip()
            brand = hxs.select("//*[@itemprop='manufacturer']/text()")
            if brand:
                res['brand'] = brand[0].extract().strip()
            res['url'] = url
            res['description'] = name
            res['price'] = price
            res['sku'] = sku
            main_ident = hxs.select('//div[@class="prod-detail-part"]'
                                    '/span[@class="prod-detail-part-value"]'
                                    '/text()')[0].extract().strip()
            res['identifier'] = main_ident if not 'option_id' in response.meta \
                else '%s-%s' % (main_ident, response.meta['option_id'])
            ident = res['identifier'].strip()
            if ident not in self._idents:
                self._idents.append(ident)
                yield load_product(res, response)
        elif options:
            event_validation = hxs.select('//*[@id="__EVENTVALIDATION"]/@value').extract()[0]
            view_state = hxs.select('//*[@id="__VIEWSTATE"]/@value').extract()[0]

            is_multioptions = hxs.select("//select[contains(@name,'ddlVariationGroup')]")
            if len(is_multioptions) < 2:
                select_name = hxs.select("//select[contains(@name,'ddlVariationGroup')]/@name").extract()[0]
                for option in options[1:]:
                    option_value = option.select('./@value')[0].extract()
                    request = FormRequest(url=response.url,
                                  formdata={u'ctl00$MainContent$ViewTypeCheckBox': u'on',
                                            u'__EVENTTARGET': select_name,
                                            u'__EVENTARGUMENT': u'',
                                            u'__EVENTVALIDATION': event_validation,
                                            u'__VIEWSTATE': view_state,
                                            select_name: option_value},
                                  meta={'option':  option.select('./text()').extract()[0].strip(),
                                        'option_id': option_value},
                                  callback=self.parse_product)
                    yield request


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
