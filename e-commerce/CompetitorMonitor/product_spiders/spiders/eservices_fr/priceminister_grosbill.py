from product_spiders.spiders.eservices_fr.priceminister_deleentech_spider import PriceministerDeleentechSpider


class PriceministerGrosbillSpider(PriceministerDeleentechSpider):
    name = 'eservicesgroup-fr-priceminister-grosbill'
    allowed_domains = ['priceminister.com']
    start_urls = ['http://www.priceminister.com/boutique/grosbill/nav']

    pages_url = 'http://www.priceminister.com/boutique/grosbill/pa/%(pa)s/nav'

    missing_urls = [
        'http://www.priceminister.com/offer?action=desc&aid=642871709&productid=221305606',
    ]
