from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class LeisureLakesBikesZyroSpider(SecondaryBaseSpider):
    name = 'zyro-leisurelakesbikes.com'
    allowed_domains = ['leisurelakesbikes.com', 'competitormonitor.com']
    csv_file = 'pedalpedal/leisurelakesbikes.csv'
    start_urls = ['http://leisurelakesbikes.com']
