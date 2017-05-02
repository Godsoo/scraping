# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class IntoTheBlueSpider(SecondaryBaseSpider):
    name = "redletterdays-intotheblue.co.uk"
    allowed_domains = ('intotheblue.co.uk', )
    start_urls = ['http://www.intotheblue.co.uk']

    csv_file = 'buyagift/intotheblue.co.uk_products.csv'
