# -*- coding: utf-8 -*-

from scrapy.item import Item, Field


class BushIndustriesMeta(Item):
    mpn = Field()
    asin = Field()

