from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class ParkerDirectSpider_C(SecondaryBaseSpider):
    name = 'arco-c-parker-direct.com'
    allowed_domains = ['parker-direct.com']
    start_urls = ('http://www.parker-direct.com/',)

    csv_file = 'arco_a/parker_crawl.csv'
