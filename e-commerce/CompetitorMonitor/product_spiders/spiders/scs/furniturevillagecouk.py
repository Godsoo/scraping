# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class FurnitureVillageSpider(SecondaryBaseSpider):
    name = "scs-furniturevillage.co.uk"
    allowed_domains = ('furniturevillage.co.uk', )
    start_urls = ['http://www.furniturevillage.co.uk/']

    csv_file = 'harveys/furniturevillage_crawl.csv'
