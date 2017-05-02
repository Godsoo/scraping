from product_spiders.base_spiders.wigglespider import WiggleSpider


class WiggleAuSpider(WiggleSpider):
    name = 'crc-us-wiggle.com'

    website_id = 391

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'USD'
    _lang_form_countryID = '18'
