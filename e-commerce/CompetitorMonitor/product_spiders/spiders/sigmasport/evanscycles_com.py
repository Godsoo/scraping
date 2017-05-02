"""

Name: sigmasport-evanscycles.com
Account: SigmaSport

IMPORTANT!!

- Please be careful, this spider will be blocked if you're not
- This spider use EvansCyclesBaseSpider
- Do not use BSM here. EvansCyclesBaseSpider uses a custom BSM

"""

from product_spiders.base_spiders import EvansCyclesBaseSpider
from sigmasportitems import SigmaSportMeta, extract_exc_vat_price
from product_spiders.items import Product


class EvansCyclesComSpider(EvansCyclesBaseSpider):
    name = 'sigmasport-evanscycles.com'

    # Copy data from products local file if exists
    secondary = True

    def parse_secondary(self, response):
        for obj in super(EvansCyclesComSpider, self).parse_secondary(response):
            if isinstance(obj, Product):
                metadata = SigmaSportMeta()
                metadata['price_exc_vat'] = extract_exc_vat_price(obj)
                obj['metadata'] = metadata
            yield obj
