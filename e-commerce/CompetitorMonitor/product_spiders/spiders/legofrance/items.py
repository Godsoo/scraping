# -*- coding: utf-8 -*-

from scrapy.item import Item, Field

class LegoFranceMeta(Item):
    seller = Field()
    total_sellers = Field()
