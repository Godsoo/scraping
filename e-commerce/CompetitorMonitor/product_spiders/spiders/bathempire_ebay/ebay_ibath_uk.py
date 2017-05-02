"""
Account: Bath Empire
Name: bathempire-ibathuk.ebay.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4592
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


from product_spiders.base_spiders.ebaystorespider import eBayStoreSpider


class iBathUKeBayStore(eBayStoreSpider):
    name = 'bathempire_ebay-ibathuk.ebay.co.uk'
    start_urls = ['http://stores.ebay.co.uk/iBathUK/_i.html?_nkw=&submit=Search']

    id_as_sku = True
