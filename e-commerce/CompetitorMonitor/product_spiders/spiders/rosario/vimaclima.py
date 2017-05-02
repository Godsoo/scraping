from basespider import BaseRosarioSpider


class VimaclimaSpider(BaseRosarioSpider):
    name = 'vimaclima.ebay'
    start_urls = ('http://stores.ebay.it/worldclima',)
