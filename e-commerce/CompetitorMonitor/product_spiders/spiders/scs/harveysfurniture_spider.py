# -*- coding: utf-8 -*-
from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider


class HarveysFurnitureSpider(SecondaryBaseSpider):
    name = "scs-harveysfurniture.co.uk"
    allowed_domains = ('harveysfurniture.co.uk', )
    start_urls = ['http://www.harveysfurniture.co.uk/']

    csv_file = 'harveys/harveysfurniture.co.uk_products.csv'
