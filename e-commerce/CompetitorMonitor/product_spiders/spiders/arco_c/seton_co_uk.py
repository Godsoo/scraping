from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class SetonCoUkSpider_B(SecondaryBaseSpider):
    name = 'arco-c-seton.co.uk'
    allowed_domains = ['seton.co.uk']
    start_urls = ('http://www.seton.co.uk/',)

    # SecondaryBaseSpider config
    csv_file = 'arco_a/seton_crawl.csv'
    json_file = 'arco_a/seton_crawl.json-lines'
