import os
import csv
import shutil

from scrapy import signals
from scrapy.xlib.pydispatch import dispatcher
try:
    from scrapy.spiders import Spider as BaseSpider
except ImportError:
    from scrapy.spider import BaseSpider
from scrapy.utils.request import request_fingerprint

from product_spiders.items import Product

HERE = os.path.abspath(os.path.dirname(__file__))

class ProductCacheSpider(BaseSpider):
    '''
Another attempt to speed up big site spiders.

The purpose of this spider is to reduce the number of HTTP requests. The main assumption
is that 'price' and 'stock' fields can be extracted from product list and other fields
don't change. That allows to update all prices in
'number of products' / 'products per page' requests instead of at least
'number of products' requests (or more if we have to check for new products).
All other fields are supplied from on-disk cache or product page is fetched for
new products.

To use this spider just inherit from it and use
yield self.fetch_product(request, product) instead of yield request.

FIXME: Does not work with sites that have multiple options for products
    '''
    by_url = {}
    by_identifier = {}
    volatile_fields = ('price', 'stock')

    id_fingerprints = set()
    url_fingerprints = set()
    _cached_cache_filename = None

    def __init__(self, *args, **kwargs):
        super(ProductCacheSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(self.store_products_to_cache, 'export_finished')
        self.load_products_from_cache()

    def _signature(self):
        ''' Signature to invalidate the cached data
            once the spider implementation changes
        '''
        import hashlib
        import inspect
        # data = inspect.getsource(ProductCacheSpider)
        # Changes to Base spider do not invalidate caches most of the time
        data = '.'
        data += inspect.getsource(self.__class__)
        return hashlib.sha1(data).hexdigest()[:7]

    def get_cache_filename(self):
        if not self._cached_cache_filename:
            self._cached_cache_filename = os.path.join(HERE,
                    'prodcache_' + self._signature() + '_' + str(self.name) + '.csv')
        return self._cached_cache_filename

    def store_products_to_cache(self, spider, stats):
        if not hasattr(spider, 'crawl_id'): return

        if spider.name == self.name:
            self.log('Store cache to %s' % (self.get_cache_filename()))
            shutil.copy('data/%s_products.csv' % spider.crawl_id,
                    self.get_cache_filename())

    def load_products_from_cache(self):
        if os.path.exists(self.get_cache_filename()):
            self.log('Cache found %s' % (self.get_cache_filename()))
            with open(self.get_cache_filename()) as f:
                reader = csv.DictReader(f)
                self.by_url = {}
                for row in reader:
                    product = Product(row)
                    product['name'] = row['name'].decode('utf-8')
                    product['category'] = row['category'].decode('utf-8')
                    product['brand'] = row['brand'].decode('utf-8')

                    self.by_url[row['url']] = Product(row)
                    self.by_identifier[row['identifier']] = Product(row)
        else:
            self.log('Cache not found %s' % (self.get_cache_filename()))

    def use_cached_product(self, product, cached):
        if not cached:
            return False

        for field in self.volatile_fields:
            if product.get(field):
                continue
            elif cached.get(field):
                # Must-have volatile field updates
                return False
        else:
            return True

    def fetch_product(self, request, product):
        '''
            Go to product page or return cached product.
            request is the same Request object you would use to fetch the product page
            product is a product with at least 'price' and 'stock' fields assigned.

            Example:
            yield self.fetch_product(Request(url, callback=...), loader.load_item())

            This method checks if product has all ProductCacheSpider.volatile_fields
            fields present and if cache has been invalidated by code changes in spider.
            - If cached product is returned it will be updated with all fields of product
            passed to this function.
            - If request to product page is made, response.meta['product'] will have
            the product passed to this function. You should use it to avoid extracting
            fields like 'price' and 'stock' again.
        '''
        if product.get('identifier'):
            if product['identifier'] in self.id_fingerprints:
                return None
            self.id_fingerprints.add(product['identifier'])

            cached = self.by_identifier.get(product['identifier'])
        else:
            fp = request_fingerprint(request)
            if fp in self.url_fingerprints:
                return None
            self.url_fingerprints.add(fp)

            cached = self.by_url.get(request.url)

        if self.use_cached_product(product, cached):
            p = Product(cached)
            for key, value in product.items():
                p[key] = value
            self.log('PRODCACHE: cached %s' % (request.url))
            return p

        #self.log('PRODCACHE: fetch %s' % (request.url))
        request.meta['product'] = product
        return request
