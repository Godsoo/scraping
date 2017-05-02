# -*- coding: utf-8 -*-
from scrapy.item import Item, Field

class FMGMeta(Item):
    discontinued = Field()
    colour = Field()
    size = Field()
    variant = Field()
    feature = Field()
