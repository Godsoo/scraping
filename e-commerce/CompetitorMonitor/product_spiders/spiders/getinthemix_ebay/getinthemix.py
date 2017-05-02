from basespider import BaseGetInTheMixEBaySpider


class GetInTheMixSpider(BaseGetInTheMixEBaySpider):
    name = 'getinthemix-ebay-getinthemix'
    start_urls = ('http://stores.ebay.co.uk/whybuynewuk/_i.html?_nkw=',)
