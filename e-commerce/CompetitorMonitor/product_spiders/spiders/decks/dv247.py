from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class DV247(SecondaryBaseSpider):
    name = 'decks-dv247.com'
    allowed_domains = ['dv247.com', 'www.dv247.com']
    start_urls = ('http://www.dv247.com',)
    csv_file = 'getinthemix/dv247_com_crawl.csv'
