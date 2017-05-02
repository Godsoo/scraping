from basespider import BaseRosarioSpider


class ClimaConfortSpider(BaseRosarioSpider):
    name = 'climaconfortsrl2010.ebay'
    start_urls = ('http://stores.ebay.it/climaconfort',)
