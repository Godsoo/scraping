from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class FfxSpider(SecondaryBaseSpider):
    name = 'powertools2u-ffx.co.uk'
    allowed_domains = ['ffx.co.uk']
    csv_file = 'ffxtools/ffx.co.uk_products.csv'
    start_urls = ['http://www.ffx.co.uk']
