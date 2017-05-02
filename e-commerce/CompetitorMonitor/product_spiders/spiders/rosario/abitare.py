from basespider import BaseRosarioSpider


class AbitareSpider(BaseRosarioSpider):
    name = 'ABITARE-SPA.ebay'
    start_urls = ('http://stores.ebay.it/abitarespa/_i.html?rt=nc&_ipg=192',)
