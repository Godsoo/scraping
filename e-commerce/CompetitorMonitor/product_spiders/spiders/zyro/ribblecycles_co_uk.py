from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class RibblecyclesZyroSpider(SecondaryBaseSpider):
    name = 'zyro-ribblecycles.co.uk'
    allowed_domains = ['ribblecycles.co.uk', 'competitormonitor.com']
    csv_file = 'sigmasport/ribblecycles.csv'
    start_urls = ['http://ribblecycles.co.uk']
