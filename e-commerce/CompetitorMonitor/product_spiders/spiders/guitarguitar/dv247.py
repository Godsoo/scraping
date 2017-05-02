# -*- coding: utf-8 -*-

from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class DV247Spider(SecondaryBaseSpider):
    name = u'guitarguitar-dv247.com'
    allowed_domains = ['dv247.com']

    start_urls = ['http://www.dv247.com']

    csv_file = 'studioxchange/dv247.com_products.csv'
