from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class TowersuppliesSpider_B(SecondaryBaseSpider):
    name = 'arco-b-towersupplies.com'
    allowed_domains = ['towersupplies.com']
    start_urls = [
        'http://www.towersupplies.com',
        ]

    csv_file = 'arco_a/towersupplies_crawl.csv'