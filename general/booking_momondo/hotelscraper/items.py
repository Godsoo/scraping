# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class HotelscraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    # pass
    name    = scrapy.Field()
    chain   = scrapy.Field()
    # occupancy = scrapy.Field()
    country = scrapy.Field()
    area    = scrapy.Field()
    rooms   = scrapy.Field()
    price   = scrapy.Field()
    street  = scrapy.Field()
