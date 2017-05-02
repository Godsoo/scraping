from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class CjsafetyCoUkSpider_B(SecondaryBaseSpider):
    name = 'arco-c-cjsafety.co.uk'
    allowed_domains = ['cjsafety.co.uk']
    start_urls = ['http://www.cjsafety.co.uk/']

    # SecondaryBaseSpider config
    csv_file = 'arco_a/cjsafety_crawl.csv'
