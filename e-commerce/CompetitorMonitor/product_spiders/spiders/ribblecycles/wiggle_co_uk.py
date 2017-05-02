import os

from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request, FormRequest
from product_spiders.base_spiders.wigglespider import WiggleSpider
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
from product_spiders.config import DATA_DIR
from product_spiders.items import Product


class RibbleCyclesWiggleSpider(SecondaryBaseSpider):
    name = 'ribblecycles-wiggle.co.uk'
    allowed_domains = ['wiggle.co.uk']

    csv_file = os.path.join(DATA_DIR, 'wiggle.co.uk_products.csv')
    is_absolute_path = True

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'GBP'
    _lang_form_countryID = '1'

    def __init__(self, *args, **kwargs):
        super(RibbleCyclesWiggleSpider, self).__init__(*args, **kwargs)

        self.product_ids = {}
        self.matched_identifiers = set()

    def closing_parse_simple(self, response):
        for item in super(RibbleCyclesWiggleSpider, self).closing_parse_simple(response):
            if isinstance(item, Product):
                if item['identifier'] in self.product_ids:
                    item['name'] = self.product_ids[item['identifier']]
                else:
                    self.product_ids[item['identifier']] = item['name']
            yield item

    def parse_product(self, response):
        for item in WiggleSpider.parse_product_main(response, self.product_ids, self.matched_identifiers):
            yield item

    def _start_requests_simple(self):
        r = Request('http://www.wiggle.co.uk', dont_filter=True,
                    meta={'callback': self._start_requests_simple2}, callback=self.get_currency)
        yield r

    def _start_requests_simple2(self, response):
        for r in super(RibbleCyclesWiggleSpider, self)._start_requests_simple():
            yield r

    def get_currency(self, response):
        hxs = HtmlXPathSelector(response)

        verification_token = hxs.select('//input[@name="__RequestVerificationToken"]/@value').extract()[0]
        yield FormRequest('http://www.wiggle.co.uk/internationaloptions/update',
                          formdata={'__RequestVerificationToken': verification_token,
                                    'langId': self._lang_form_lang_id,
                                    'currencyId': self._lang_form_currencyID,
                                    'countryId': self._lang_form_countryID,
                                    'action': 'Update',
                                    'returnUrl': '/',
                                    'cancelUrl': '/'},
                          dont_filter=True,
                          callback=response.meta['callback'])
