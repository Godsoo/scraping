# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider

class JunoSpider(SecondaryBaseSpider):

    name = "getinthemix-juno.co.uk"
    start_urls = ["http://www.juno.co.uk"]
    allowed_domains = ['juno.co.uk']

    csv_file = 'studioxchange/juno.co.uk_products.csv'    
