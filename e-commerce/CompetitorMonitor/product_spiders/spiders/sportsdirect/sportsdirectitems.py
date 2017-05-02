# -*- coding: utf-8 -*-
from scrapy.item import Item, Field

class SportsDirectMeta(Item):
    size = Field()
    rrp = Field()
    product_code = Field()

