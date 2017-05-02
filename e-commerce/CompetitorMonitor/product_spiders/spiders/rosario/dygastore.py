from basespider import BaseRosarioSpider


class DygaStoreSpider(BaseRosarioSpider):
    name = 'dyga-store.ebay'
    start_urls = ('http://stores.ebay.it/promoclima/',)
