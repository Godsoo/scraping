from product_spiders.base_spiders.unified_marketplace_spider import UnifiedMarketplaceSpider
from product_spiders.base_spiders.primary_spider import PrimarySpider


class LakelandAmazonSpider(UnifiedMarketplaceSpider, PrimarySpider):
    name = 'lakeland-amazon.co.uk-marketplace'
    market_type = "marketplace"
    data_filename = 'lakeland_amazon'
    start_urls = ['http://amazon.co.uk']

    csv_file = 'lakeland_amazon_marketplace_as_prim.csv'

