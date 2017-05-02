from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class ChainReactionCyclesComZyroSpider(SecondaryBaseSpider):
    name = 'zyro-chainreactioncycles.com'
    allowed_domains = ['chainreactioncycles.com', 'competitormonitor.com']
    csv_file = 'pedalpedal/crcukfeed.csv'
    start_urls = ['http://chainreactioncycles.com']
