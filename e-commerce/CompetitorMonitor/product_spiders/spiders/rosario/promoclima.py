from basespider import BaseRosarioSpider


class PromoclimaSpider(BaseRosarioSpider):
    name = 'promoclima.ebay'
    start_urls = ('http://stores.ebay.it/promoclima/',)
