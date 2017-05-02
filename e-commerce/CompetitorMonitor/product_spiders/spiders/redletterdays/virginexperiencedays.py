# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class VirginExperienceDaysSpider(SecondaryBaseSpider):
    name = "redletterdays-virginexperiencedays.co.uk"
    allowed_domains = ('virginexperiencedays.co.uk', )
    start_urls = ['http://www.virginexperiencedays.co.uk']

    csv_file = 'buyagift/virginexperiencedays.co.uk_products.csv'
