from basespider import BaseRosarioSpider


class CatexclimaSpider(BaseRosarioSpider):
    name = 'catexclima.ebay'
    start_urls = ('http://stores.ebay.it/catexclima',)
