"""
Gear4Music secondary spider
Original ticket: https://www.assembla.com/spaces/competitormonitor/tickets/4598-guitar-guitar-%7C-gear4music-%7C-secondary-spider-/details
"""

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class Gear4Music(SecondaryBaseSpider):
    name = 'guitarguitar-gear4music.com'
    allowed_domains = ['gear4music.com']
    start_urls = ('http://www.gear4music.com',)
    csv_file = 'getinthemix/gear4music_crawl.csv'
