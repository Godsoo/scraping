from product_spiders.base_spiders.wigglespider import WiggleSpider


class WiggleEsSpider(WiggleSpider):
    name = 'wiggle.com-de'

    website_id = 760

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'EUR'
    _lang_form_countryID = '9'
