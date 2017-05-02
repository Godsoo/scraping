from product_spiders.spiders.studioxchange.kmraudio_com import KmrAudioSpider
from decimal import Decimal

class KMRAudioSpider2(KmrAudioSpider):
    name = "kmraudio-kmraudio"

    def parse_product(self, response):
        for item in super(KMRAudioSpider2, self).parse_product(response):
            if item['price'] and Decimal(item['price']) < 99:
                item['shipping_cost'] = 10
            else:
                item['shipping_cost'] = 0

            item['category'] = item['brand']
            item['sku'] = item['identifier']
            yield item
