from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class AlexandraSpider_B(SecondaryBaseSpider):
    name = 'arco-b-alexandra.co.uk'
    allowed_domains = ['alexandra.co.uk']
    start_urls = ['http://www.alexandra.co.uk']
    csv_file = 'arco_a/alexandra.co.uk_crawl.csv'
