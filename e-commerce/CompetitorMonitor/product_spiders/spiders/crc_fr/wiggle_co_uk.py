from product_spiders.base_spiders.wigglespider import WiggleSpider


class WiggleFrSpider(WiggleSpider):
    name = 'crc-fr-wiggle.com'

    website_id = 406

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'EUR'
    _lang_form_countryID = '11'
