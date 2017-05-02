from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class BigDugSpider_C(SecondaryBaseSpider):
    name = 'arco-c-bigdug.co.uk'

    allowed_domains = ['bigdug.co.uk']
    start_urls = ('http://www.bigdug.co.uk',)

    csv_file = 'arco_a/bigdugcouk_crawl.csv'
