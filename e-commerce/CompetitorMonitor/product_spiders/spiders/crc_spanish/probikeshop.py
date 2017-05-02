from scrapy.http import Request, FormRequest

from product_spiders.spiders.crc_fr.probikeshop import ProBikeShopSpider as ProBikeShopSpiderFr

class ProBikeShopSpiderEs(ProBikeShopSpiderFr):
    name = 'crc_sp-probikeshop.fr'
    allowed_domains = ['probikeshop.es', 'www.probikeshop.es', 'probikeshop.com', 'www.probikeshop.com']
    start_urls = ('http://www.probikeshop.com',)

    def start_requests(self):
        yield Request('http://www.probikeshop.com', callback=self.change_country)

    def change_country(self, response):
        req = FormRequest.from_response(response, formname='form-customer-preferences',
                                        formdata={'country[countriesId]': '195',
                                                  'currency[id]': '1',
                                                  'language[languagesId]': '20'})
        yield req

    def parse_product(self, response):
        for item in super(ProBikeShopSpiderEs, self).parse_product(response):
            item['url'] = item['url']
            yield item
