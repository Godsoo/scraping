# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class Camelbak(SecondaryBaseSpider):
    name = "camelbak_fr-camelbak.com"
    start_urls = ["http://www.camelbak.com"]
    allowed_domains = ['camelbak.com']

    csv_file = 'camelbak_de/camelbak.com_products.csv'
