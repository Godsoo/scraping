from product_spiders.base_spiders.wigglespider import WiggleSpider

from product_spiders.base_spiders.primary_spider import PrimarySpider


class WiggleSpider(PrimarySpider, WiggleSpider):
    name = 'wiggle.co.uk'

    website_id = 484948

    csv_file = 'wiggle.co.uk_products.csv'
    use_data_dir = True

    _lang_form_lang_id = 'en'
    _lang_form_currencyID = 'GBP'
    _lang_form_countryID = '1'
