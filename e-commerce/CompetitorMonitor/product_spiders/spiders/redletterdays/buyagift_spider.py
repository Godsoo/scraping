# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class BuyagiftSpider(SecondaryBaseSpider):
    name = "redletterdays-buyagift.co.uk"
    allowed_domains = ('buyagift.co.uk', )
    start_urls = ('http://www.buyagift.co.uk',)

    csv_file = 'buyagift/buyagift.co.uk_products.csv'
