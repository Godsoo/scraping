import csv
import codecs
import cStringIO
import os
import copy
import json
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, HtmlResponse, FormRequest
from scrapy.utils.response import get_base_url
from scrapy.utils.url import urljoin_rfc
from scrapy.http.cookies import CookieJar

from product_spiders.items import Product, ProductLoader

HERE = os.path.abspath(os.path.dirname(__file__))

KEYS = ['AIzaSyDmC2E8OgTrtikhGt5OlVaY8GqqSu696KE',
        'AIzaSyCut3AS5hpo63CcZopV5Bs2wxbYd9IB2II',
        'AIzaSyAVHD41ZbqwyA4KF-U4tqCy_y71YGfZ_nQ', ]

class GoogleSpider(BaseSpider):
    name = 'google.com_DO'
    allowed_domains = ['googleapis.com']

    VALID_PERC = Decimal(0.4)

    def start_requests(self):
        with open(os.path.join(HERE, 'skus_prices.csv')) as f_prices:
            reader = csv.DictReader(f_prices)
            for i, row in enumerate(reader):
                query = (row['name']).replace(' ', '+')
                url = 'https://www.googleapis.com/shopping/search/v1/public/products' + \
                      '?key=%s&country=US&' + \
                      'q=%s&rankBy=price%%3Aascending'

                yield Request(url % (KEYS[i % len(KEYS)], query),
                              meta={'sku': row['sku'],
                                    'price': row['price']})

    def parse(self, response):
        data = json.loads(response.body)
        if not data['totalItems']:
            return

        i = 0
        found = False
        total = len(data['items'])

        while not found and i < total:
            item = data['items'][i]
            i += 1
            price = str(data['items'][0]['product']['inventories'][0]['price'])
            if not 'dyersonline.com' in item['product']['link'] and \
                self._check_valid_price(response.meta['price'], price):
                    found = True
                    pr = Product()
                    pr['name'] = (item['product']['title'] + ' ' + item.get('product', {})
                                  .get('author', {}).get('name', '')).strip()
                    pr['url'] = item['product']['link']
                    pr['price'] = Decimal(price)
                    if item['product']['images']:
                        try:
                            pr['image_url'] = item['product']['images'][0]['link']
                        except:
                            pass
                    pr['brand'] = item['product'].get('brand', '')
                    pr['sku'] = response.meta['sku']
                    pr['identifier'] = response.meta['sku']

                    yield pr

    def _check_valid_price(self, site_price, price):
        if not site_price:
            site_price = price
        p1 = Decimal(site_price)
        p2 = Decimal(price)

        return p1 - p1 * self.VALID_PERC <= p2 <= p1 + p2 * self.VALID_PERC


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
