from basespider import BaseGetInTheMixEBaySpider


class EssexSpider(BaseGetInTheMixEBaySpider):
    name = 'getinthemix-ebay-essex'
    start_urls = ('http://stores.ebay.co.uk/DJ-Disco-and-PA-Equipment',)

    collect_stock = True
