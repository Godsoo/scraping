from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class WorkWeaErxpressSpider_B(SecondaryBaseSpider):
    name = 'arco-b-workwearexpress.com'
    allowed_domains = ['workwearexpress.com']
    start_urls = ('http://www.workwearexpress.com/',)

    csv_file = 'arco_a/workwearexpress_crawl.csv'
