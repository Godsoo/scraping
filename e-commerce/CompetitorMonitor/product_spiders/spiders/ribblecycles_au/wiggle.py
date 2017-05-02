from product_spiders.base_spiders.wigglespider import WiggleSpider


class WiggleAuSpider(WiggleSpider):
    name = 'ribblecycles_au-wiggle.com'

    website_id = 350

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'AUD'
    _lang_form_countryID = '27'

    def full_run_required(self):
        return True