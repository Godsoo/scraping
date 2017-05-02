# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class GuitarGuitarSpider(SecondaryBaseSpider):

    name = "gear4music-guitarguitar.co.uk"
    start_urls = ["http://www.guitarguitar.co.uk"]
    allowed_domains = ['guitarguitar.co.uk']

    csv_file = 'guitarguitar/guitarguitar.co.uk_products.csv'