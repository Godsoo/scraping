from product_spiders.spiders.eservices_fr.priceminister_deleentech_spider import PriceministerDeleentechSpider


class PriceministerBuyFiveSpider(PriceministerDeleentechSpider):
    name = 'eservicesgroup-fr-priceminister-buyfive'
    allowed_domains = ['priceminister.com']
    start_urls = ['http://www.priceminister.com/boutique/buyFIVE/nav']

    pages_url = 'http://www.priceminister.com/boutique/buyFIVE/pa/%(pa)s/nav'
