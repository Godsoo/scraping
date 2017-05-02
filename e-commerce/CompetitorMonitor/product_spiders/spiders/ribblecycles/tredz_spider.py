# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class TredzSpider(SecondaryBaseSpider):

    name = "ribblecycles-tredz.co.uk"
    start_urls = ["http://www.tredz.co.uk"]
    allowed_domains = ['tredz.co.uk']

    csv_file = 'sigmasport/tredz.co.uk_crawl.csv'    
