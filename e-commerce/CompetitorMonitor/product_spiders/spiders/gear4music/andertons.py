# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class AndertonsSpider(SecondaryBaseSpider):

    name = "gear4music-andertons.co.uk"
    start_urls = ["https://www.andertons.co.uk"]
    allowed_domains = ['andertons.co.uk']

    csv_file = 'guitarguitar/andertons.co.uk_products.csv'