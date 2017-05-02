from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class CromwellCoUkSpider_B(SecondaryBaseSpider):
    name = 'arco-c-cromwell.co.uk'
    allowed_domains = ['cromwell.co.uk']
    start_urls = ('http://www.cromwell.co.uk/',)

    csv_file = 'arco_a/cromwell_crawl.csv'
