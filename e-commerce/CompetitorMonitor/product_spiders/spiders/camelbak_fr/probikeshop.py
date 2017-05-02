from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class AlltricksSpider(SecondaryBaseSpider):
    name = "camelbak_fr-probikeshop.fr"
    allowed_domains = ('probikeshop.fr', )
    start_urls = ('http://www.probikeshop.fr',)
    csv_file = 'crc_fr/probikeshop_crawl.csv'
