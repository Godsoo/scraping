import os

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
from product_spiders.config import DATA_DIR


class ZyroWiggleSpider(SecondaryBaseSpider):
    name = "zyro-wiggle.co.uk"
    allowed_domains = ('wiggle.co.uk', )
    start_urls = ('http://www.wiggle.co.uk', )

    csv_file = os.path.join(DATA_DIR, 'wiggle.co.uk_products.csv')
    is_absolute_path = True
