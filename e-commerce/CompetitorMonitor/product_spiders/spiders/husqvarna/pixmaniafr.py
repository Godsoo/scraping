from scrapy.http import Request
from product_spiders.base_spiders import PixmaniaBaseSpider


class PixmaniaSpider(PixmaniaBaseSpider):
    name = u'pixmania.fr'
    allowed_domains = ['pixmania.fr']
    start_urls = [u'http://www.pixmania.fr']

    collect_reviews = True
    filters_enabled = False
    use_main_id_as_sku = True

    def start_requests(self):
        urls = ['http://www.pixmania.fr/petit-electromenager/aspirateur-et-nettoyeur-443-m.html',
                'http://www.pixmania.fr/bricolage/outillage-a-main-2751-m.html',
                'http://www.pixmania.fr/jardin/outillage-a-main-2042-m.html']

        for url in urls:
            yield Request(url)
