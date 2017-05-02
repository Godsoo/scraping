import os
from product_spiders.base_spiders.wigglespider import WiggleSpider as BaseWiggleSpider
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
from product_spiders.config import DATA_DIR

class WiggleSpider(SecondaryBaseSpider):
    name = "tweekscycles-wiggle.co.uk"
    allowed_domains = ['wiggle.co.uk']

    csv_file = os.path.join(DATA_DIR, 'wiggle.co.uk_products.csv')
    is_absolute_path = True

    product_ids = {}

    def parse_product(self, response):
        for item in BaseWiggleSpider.parse_product_main(response, self.product_ids, self.matched_identifiers):
            yield item
