from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class TowersuppliesSpider_C(SecondaryBaseSpider):
    name = 'arco-c-towersupplies.com'
    allowed_domains = ['towersupplies.com']
    start_urls = [
        'http://www.towersupplies.com',
        ]

    csv_file = 'arco_a/towersupplies_crawl.csv'