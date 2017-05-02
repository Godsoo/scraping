# -*- coding: utf-8 -*-
from scrapy.item import Item, Field


class EServiceGroupMeta(Item):
    upc = Field()
    mpn = Field()