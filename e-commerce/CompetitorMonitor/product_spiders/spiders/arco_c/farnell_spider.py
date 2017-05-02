from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class FarnellSpider_C(SecondaryBaseSpider):
    name = 'arco-c-farnell.com'
    allowed_domains = ['farnell.com']
    start_urls = ('http://cpc.farnell.com/',)

    csv_file = 'arco_a/farnell_crawl.csv'
