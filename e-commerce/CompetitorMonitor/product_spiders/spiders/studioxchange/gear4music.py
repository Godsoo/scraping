from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class Gear4Music(SecondaryBaseSpider):
    name = 'studioxchange-gear4music.com'
    allowed_domains = ['gear4music.com']
    start_urls = ('http://www.gear4music.com',)
    csv_file = 'getinthemix/gear4music_crawl.csv'
