from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class AlltricksSpider(SecondaryBaseSpider):
    name = "crc_sp-alltricks.com"
    allowed_domains = ('alltricks.com', )
    start_urls = ('http://www.alltricks.com',)
    csv_file = 'crc_fr/alltricks_crawl.csv'
