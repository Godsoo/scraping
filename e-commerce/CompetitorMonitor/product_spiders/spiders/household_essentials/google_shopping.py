import os
import csv
from product_spiders.base_spiders import GoogleShoppingBaseSpider


HERE = os.path.abspath(os.path.dirname(__file__))


class GoogleShoppingSpider(GoogleShoppingBaseSpider):
    name = 'householdessentials-googleshopping'
    allowed_domains = ['google.com']
    start_urls = ['https://www.google.com/shopping?hl=en']

    SHOPPING_URL = 'https://www.google.com/shopping?hl=en'
    ACTIVE_BROWSERS = 20
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 5.1; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (Windows NT 6.2; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:24.0) Gecko/20100101 Firefox/24.0',
        'Mozilla/5.0 (X11; Linux x86_64; rv:24.0) Gecko/20100101 Firefox/24.0',
    ]

    parse_reviews = True

    def search_iterator(self):
        products = []
        with open(os.path.join(HERE, 'householdessentials_products.csv')) as f:
            products = list(csv.DictReader(f))

        for row in products:
            search = '00' + row['UPC']
            meta = {'sku': row['Item Number'],
                    'brand': row.get('Brand', '')}
            yield (search, meta, ['sku', 'brand'])
