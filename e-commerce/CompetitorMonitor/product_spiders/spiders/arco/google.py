import csv
import os
import json
import urllib2
from decimal import Decimal

from scrapy.spider import BaseSpider
from scrapy.http import Request

from pricecheck import valid_price

from product_spiders.items import Product

HERE = os.path.abspath(os.path.dirname(__file__))

KEYS = ('AIzaSyCeF6j5AK_TEbdyItcZVBOvEBu9kEYq6vw',)

FILTER_DOMAINS = ('arco', 'ebay')

class GoogleSpider(BaseSpider):
    name = 'arco-googleapis.com'
    allowed_domains = ['googleapis.com']

    def __init__(self, *args, **kwargs):
        super(GoogleSpider, self).__init__(*args, **kwargs)
        self.identifiers = {}
        with open(os.path.join(HERE, 'arco_products.csv')) as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.identifiers[row['url']] = row['sku']

    def start_requests(self):
        with open(os.path.join(HERE, 'arco_products.csv')) as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                sku = row['sku']

                query = _filter_str(row['name'])
                url = 'https://www.googleapis.com/shopping/search/v1/public/products' + \
                      '?key=%s&country=GB&' + \
                      'q=%s&restrictBy=condition=new'

                yield Request(url % (KEYS[i % len(KEYS)], urllib2.quote(query)), meta={'sku': sku,
                                                                        'price': row['price'].replace(',', '.').replace('$', '')})

    def _get_item(self, data, i, response):
        if i >= len(data.get('items', [])):
            return

        item = data['items'][i]
        pr = Product()
        pr['name'] = (item['product']['title'] + ' ' + item.get('product', {}).get('author', {}).get('name', '')).strip()
        pr['url'] = item['product']['link']

        price = data['items'][i]['product']['inventories'][0]['price']
        price = Decimal(str(price))
        if not 'fosterindustrial.co.uk' in pr['url']:
            price = round(price / Decimal(1.2), 2)
        pr['price'] = price

        pr['sku'] = response.meta['sku']
        pr['identifier'] = response.meta['sku']

        return pr, item

    def parse(self, response):
        data = json.loads(response.body)
        i = 0

        #Extract the mpns of the first product.
        mpns = data['items'][0]['product'].get('mpns',[''])[0]
        if mpns:
            #Search for the lowest price for the products with the same mpns
            lowest = None
            data_mpns = {'items': [item for item in data['items'] if item['product'].get('mpns',[''])[0].lower()==mpns.lower()]}
            while True:
                res = self._get_item(data_mpns, i, response)
                if not res:
                    break
                pr = res[0]
                item = res[1]
                invalid_domain = any([self._check_domain(domain, pr['url']) for domain in FILTER_DOMAINS])
                if invalid_domain:
                    i += 1
                else:
                    if valid_price(response.meta['price'], pr['price']) and \
                        (lowest is None or lowest['price'] > pr['price']):
                        lowest = pr
                    i += 1
            if lowest:
                yield lowest
        else:
            #Search for the first product with a valid price range.
            first_valid = None
            while True:
                res = self._get_item(data, i, response)
                if not res:
                    break
                pr = res[0]
                item = res[1]
                invalid_domain = any([self._check_domain(domain, pr['url']) for domain in FILTER_DOMAINS])
                if invalid_domain:
                    i += 1
                else:
                    if valid_price(response.meta['price'], pr['price']):
                        first_valid = pr
                        break
                    i += 1
            if first_valid:
                yield first_valid

    def _check_domain(self, domain, url):
        if domain in url:
            return True

def _filter_str(s):
    trim_strs = [
        "&trade;",
        "&reg;"
    ]
    res = s
    for trim_str in trim_strs:
        res = res.replace(trim_str, "")

    return res
