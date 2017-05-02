import re

from product_spiders.items import Product
from product_spiders.base_spiders import PixmaniaBaseSpider


class PixmaniaSpider(PixmaniaBaseSpider):
    name = "legofrance-pixmania.com"
    allowed_domains = ['pixmania.fr']
    start_urls = ('http://www.pixmania.fr/jouets-garcon/lego-2737-m.html',)

    re_sku = re.compile('(\d\d\d\d\d?)')

    filters_enabled = False

    def parse_product(self, response):
        for item in super(PixmaniaSpider, self).parse_product(response):
            if isinstance(item, Product):
                sku = self.re_sku.findall(item['name'])
                if sku:
                    item['sku'] = sku[0].strip()
                item['brand'] = 'LEGO'

            yield item

    def parse_sellers(self, response):
        for item in super(PixmaniaSpider, self).parse_sellers(response):
            if isinstance(item, Product):
                sku = self.re_sku.findall(item['name'])
                if sku:
                    item['sku'] = sku[0].strip()
                item['brand'] = 'LEGO'

            yield item
