# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class StudioxchangeSpider(SecondaryBaseSpider):
    name = "kmraudio-studioxchange"
    allowed_domains = ["studioxchange.co.uk"]
    start_urls = (
        "http://shop.studioxchange.co.uk/",
    )
    
    csv_file = 'studioxchange/studioxchange_crawl.csv'
