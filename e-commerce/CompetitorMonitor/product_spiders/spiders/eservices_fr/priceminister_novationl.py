from product_spiders.spiders.eservices_fr.priceminister_deleentech_spider import PriceministerDeleentechSpider


class PriceministerNovationSpider(PriceministerDeleentechSpider):
    name = 'eservicesgroup-fr-priceminister-novation'
    allowed_domains = ['priceminister.com']
    start_urls = ['http://www.priceminister.com/boutique/NovationI/nav']

    pages_url = 'http://www.priceminister.com/boutique/NovationI/pa/%(pa)s/nav'
