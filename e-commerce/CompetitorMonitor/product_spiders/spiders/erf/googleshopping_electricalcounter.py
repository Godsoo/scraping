import os
import csv
import shutil
from product_spiders.base_spiders import GoogleShoppingBaseSpider
from product_spiders.config import DATA_DIR
from product_spiders.items import Product
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


HERE = os.path.abspath(os.path.dirname(__file__))


class ErfGoogleShoppingElectricalcounter(GoogleShoppingBaseSpider):
    name = 'erf-googleshopping.electricalcounter'
    allowed_domains = ['google.co.uk']
    start_urls = ['https://www.google.co.uk/shopping']

    DEALER_NAME = 'The Electrical Counter'

    ALL_PRODUCTS_FILE = 'erf_google_products.csv'

    GOOGLE_DOMAIN = 'google.co.uk'
    SHOPPING_URL = 'https://www.google.co.uk/shopping'
    ACTIVE_BROWSERS = 10
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1'
        'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0',
        'Mozilla/5.0 (Windows NT 5.1; rv:31.0) Gecko/20100101 Firefox/31.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:25.0) Gecko/20100101 Firefox/25.0',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.1',
        'Mozilla/5.0 (Windows NT 6.3; rv:36.0) Gecko/20100101 Firefox/36.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10; rv:33.0) Gecko/20100101 Firefox/33.0',
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (X11; Linux i586; rv:31.0) Gecko/20100101 Firefox/31.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (Windows NT 6.0; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:24.0) Gecko/20100101 Firefox/24.0',
    ]

    filter_sellers = [
        'The Electrical Counter',
        '! RS Electrical Supplies',
        'RS Components UK',
        'Screwfix.com',
        'TLC Electrical',
    ]

    def __init__(self, *args, **kwargs):
        super(ErfGoogleShoppingElectricalcounter, self).__init__(*args, **kwargs)

        dispatcher.connect(self.lso_google_spider_closed, signals.spider_closed)

        self.file_ = open(os.path.join(DATA_DIR, self.ALL_PRODUCTS_FILE + '.tmp'), 'w')
        fieldnames = Product.fields.keys()
        fieldnames = filter(lambda f: f not in ['image_url', 'stock', 'metadata'], fieldnames)
        self.all_products_writer = csv.DictWriter(self.file_, fieldnames)
        self.all_products_writer.writeheader()

    def lso_google_spider_closed(self, spider):
        self.file_.close()
        shutil.copy(self.ALL_PRODUCTS_FILE + '.tmp', self.ALL_PRODUCTS_FILE)

    def search_iterator(self):
        products = []
        with open(os.path.join(HERE, 'ProductFeed.csv')) as f:
            products = list(csv.DictReader(f))

        for row in products:
            search = row['SKU']
            meta = {'sku': row['SKU'],
                    'brand': row.get('Manufacturer', '')}
            yield (search, meta, ['sku', 'brand'])

    def load_item_(self, *args, **kwargs):
        item = super(ErfGoogleShoppingElectricalcounter, self).load_item_(*args, **kwargs)
        if item:
            new_item = {}
            for k, v in item.iteritems():
                if isinstance(v, unicode):
                    new_item[k] = v.encode('utf-8')
                else:
                    new_item[k] = v
            self.all_products_writer.writerow(new_item)
            if self.DEALER_NAME == item['dealer']:
                return item
        return None
