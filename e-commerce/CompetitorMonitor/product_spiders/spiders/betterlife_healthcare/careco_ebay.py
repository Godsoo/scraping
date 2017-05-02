from basespider import BaseEbaySpider


class CareCoEbaySpider(BaseEbaySpider):
    name = u'betterlife_healthcare-careco-ebay'
    start_urls = ('http://stores.ebay.co.uk/CareCo-Mobility/_i.html?_nkw=&submit=Search&_ipg=192',)
 
