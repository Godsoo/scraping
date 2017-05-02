from product_spiders.spiders.eservices_fr.priceminister_deleentech_spider import PriceministerDeleentechSpider


class PriceministerExportpriveSpider(PriceministerDeleentechSpider):
    name = 'eservicesgroup-fr-priceminister-exportprive'
    allowed_domains = ['priceminister.com']
    start_urls = ['http://www.priceminister.com/boutique/exportprive/nav']

    pages_url = 'http://www.priceminister.com/boutique/exportprive/pa/%(pa)s/nav'
