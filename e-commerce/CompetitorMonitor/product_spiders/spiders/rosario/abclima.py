from basespider import BaseRosarioSpider


class AbclimacSpider(BaseRosarioSpider):
    name = 'abclima.ebay'
    start_urls = ('http://stores.ebay.it/AbClima',)
