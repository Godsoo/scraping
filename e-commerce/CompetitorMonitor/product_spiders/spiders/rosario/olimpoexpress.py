from basespider import BaseRosarioSpider


class OlimpoexpressSpider(BaseRosarioSpider):
    name = 'olimpoexpress.ebay'
    start_urls = ('http://stores.ebay.it/OLIMPOEXPRESS',)
