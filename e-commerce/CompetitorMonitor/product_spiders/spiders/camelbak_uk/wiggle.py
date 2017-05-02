# -*- coding: utf-8 -*-


"""
Account: CamelBak UK
Name: camelbak-wiggle.co.uk
Ticket link: https://www.assembla.com/spaces/competitormonitor/tickets/4611
Original developer: Emiliano M. Rudenick <emr.frei@gmail.com>
"""


from scrapy import Spider, Request, FormRequest
from product_spiders.base_spiders.wigglespider import WiggleSpider


class CamelBakWiggle(Spider):
    name = 'camelbak-wiggle.co.uk'
    allowed_domains = ['wiggle.co.uk']

    start_urls = ['http://www.wiggle.co.uk/camelbak/?ps=96']

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'GBP'
    _lang_form_countryID = '1'

    def __init__(self, *args, **kwargs):
        super(CamelBakWiggle, self).__init__(*args, **kwargs)

        self.product_ids = {}
        self.matched_identifiers = set()

    def start_requests(self):
        yield Request('http://www.wiggle.co.uk',
                      dont_filter=True,
                      callback=self.get_currency)

    def get_currency(self, response):
        verification_token = response.xpath('//input[@name="__RequestVerificationToken"]/@value').extract()[0]
        yield FormRequest('http://www.wiggle.co.uk/internationaloptions/update',
                          formdata={'__RequestVerificationToken': verification_token,
                                    'langId': self._lang_form_lang_id,
                                    'currencyId': self._lang_form_currencyID,
                                    'countryId': self._lang_form_countryID,
                                    'action': 'Update',
                                    'returnUrl': '/',
                                    'cancelUrl': '/'},
                          dont_filter=True,
                          callback=self.init_requests)

    def init_requests(self, response):
        for url in self.start_urls:
            yield Request(url)

    def parse(self, response):
        next_page = response.xpath('//div[@id="pagerMainColumnHeader"]//a[normalize-space(text())=">"]/@href').extract()
        if next_page:
            yield Request(url=next_page[0], callback=self.parse_product_list)

        products = response.xpath('//a[@data-ga-action="Product Title"]/@href').extract()
        if products:
            for product in products:
                yield Request(url=product, callback=self.parse_product)


    def parse_product(self, response):
        for item in WiggleSpider.parse_product_main(response,
            self.product_ids, self.matched_identifiers):
                yield item
