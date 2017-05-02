"""
Account: Bath Empire
Name: bathempire-radiatorshop.ebay.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4593
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


from product_spiders.base_spiders.ebaystorespider import eBayStoreSpider


class RadiatorShopeBayStore(eBayStoreSpider):
    name = 'bathempire_ebay-radiatorshop.ebay.co.uk'
    start_urls = ['http://stores.ebay.co.uk/UK-radiator-shop/_i.html?_nkw=&submit=Search']

    id_as_sku = True
