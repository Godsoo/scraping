from basespider import BaseEbaySpider


class MobilityChoicesSpider(BaseEbaySpider):
    name = u'betterlife_healthcare-mobilitychoices-ebay'
    start_urls = ('http://stores.ebay.co.uk/mobilitychoices/_i.html?_nkw=&_armrs=1&_from=&_ipg=',)
 
