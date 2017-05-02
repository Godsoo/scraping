from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class AlexandraSpider_C(SecondaryBaseSpider):
    name = 'arco-c-alexandra.co.uk'
    allowed_domains = ['alexandra.co.uk']
    start_urls = ['http://www.alexandra.co.uk']
    csv_file = 'arco_a/alexandra.co.uk_crawl.csv'
