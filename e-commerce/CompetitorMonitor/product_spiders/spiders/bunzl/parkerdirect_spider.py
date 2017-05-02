from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class ParkerDirectSpider_B(SecondaryBaseSpider):
    name = 'bunzl-parker-direct.com'
    allowed_domains = ['parker-direct.com']
    start_urls = ('http://www.parker-direct.com/',)

    csv_file = 'arco_a/parker_crawl.csv'