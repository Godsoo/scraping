from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
from decimal import Decimal

from sigmasportitems import SigmaSportMeta, extract_exc_vat_price

class ChainReactionCyclesComSpider(SecondaryBaseSpider):
    name = 'sigmasport-chainreactioncycles.com'
    allowed_domains = ['chainreactioncycles.com', 'competitormonitor.com']
    csv_file = 'pedalpedal/crcukfeed.csv'
    start_urls = ['http://chainreactioncycles.com']

    def preprocess_product(self, item):
        metadata = SigmaSportMeta()
        metadata['price_exc_vat'] = extract_exc_vat_price(item)
        item['metadata'] = metadata
        if Decimal(item['price']) < 9:
            item['shipping_cost'] = 2
        return item
