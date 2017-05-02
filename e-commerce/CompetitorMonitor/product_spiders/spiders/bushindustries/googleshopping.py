import os
import csv
import shutil
from product_spiders.base_spiders import GoogleShoppingBaseSpider
from product_spiders.config import DATA_DIR
from product_spiders.items import Product
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals


HERE = os.path.abspath(os.path.dirname(__file__))


class BushIndustriesGoogleShopping(GoogleShoppingBaseSpider):
    name = 'bushindustries-googleshopping'
    allowed_domains = ['google.com']
    start_urls = ['https://www.google.com/shopping?hl=en']

    proxy_service_location = 'us'

    parse_all = True
    parse_reviews = True

    GOOGLE_DOMAIN = 'google.com'
    SHOPPING_URL = 'https://www.google.com/shopping?hl=en'
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

    def search_iterator(self):
        products = []
        with open(os.path.join(HERE, 'bush_industries_flat_file.csv')) as f:
            products = list(csv.DictReader(f))

        for row in products:
            search = row['MPN']
            meta = {'sku': row['MPN']}
            if search:
                yield (search, meta, ['sku'])
