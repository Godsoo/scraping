from product_spiders.base_spiders.wigglespider import WiggleSpider

from scrapy import log


class WiggleSpider(WiggleSpider):
    name = 'hargrovescycles-wiggle.co.uk'

    website_id = 1364

    do_full_run = True

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'GBP'
    _lang_form_countryID = '1'

    def full_run_required(self):
        return True
