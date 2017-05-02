# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class OakFurnitureLandSpider(SecondaryBaseSpider):
    name = "scs-oakfurnitureland.co.uk"
    allowed_domains = ('oakfurnitureland.co.uk', )
    start_urls = ['http://www.oakfurnitureland.co.uk']

    csv_file = 'harveys/oakfurnitureland.co.uk_products.csv'
