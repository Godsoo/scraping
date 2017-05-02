from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class BuckandhickmanComSpider_B(SecondaryBaseSpider):
    name = 'arco-c-buckandhickman.com'
    allowed_domains = ['buckandhickman.com']
    start_urls = ('http://www.buckandhickman.com/',)

    csv_file = 'arco_a/buckandhickman_crawl.csv'