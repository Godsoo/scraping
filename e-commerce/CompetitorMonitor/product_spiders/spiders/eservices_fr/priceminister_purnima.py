from product_spiders.spiders.eservices_fr.priceminister_deleentech_spider import PriceministerDeleentechSpider


class PriceministerPurnimaSpider(PriceministerDeleentechSpider):
    name = 'eservicesgroup-fr-priceminister-purnima-digi'
    allowed_domains = ['priceminister.com']
    start_urls = ['http://www.priceminister.com/boutique/purnima-digi/nav']

    pages_url = 'http://www.priceminister.com/boutique/purnima-digi/pa/%(pa)s/nav'

    missing_urls = [
        'http://www.priceminister.com/offer?action=desc&aid=691622974&productid=109546367',
        'http://www.priceminister.com/offer?action=desc&aid=732179850&productid=240724768',
        'http://www.priceminister.com/offer?action=desc&aid=1327187152&productid=235885966',
        'http://www.priceminister.com/offer?action=desc&aid=691622974&productid=109546367',
        'http://www.priceminister.com/offer?action=desc&aid=691623165&productid=251481669',
        'http://www.priceminister.com/offer?action=desc&aid=691623161&productid=238088184',
        'http://www.priceminister.com/offer?action=desc&aid=692972128&productid=181454768',
        'http://www.priceminister.com/offer?action=desc&aid=714520441&productid=270887900',
        'http://www.priceminister.com/offer?action=desc&aid=858687356&productid=364852231',
        'http://www.priceminister.com/offer?action=desc&aid=691623055&productid=201102320',
    ]
