# -*- coding: utf-8 -*-
from scrapy.item import Item, Field

class LeCreusetMeta(Item):
    promotion = Field()
    asin = Field()

