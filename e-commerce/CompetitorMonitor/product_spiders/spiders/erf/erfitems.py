# -*- coding: utf-8 -*-

from scrapy.item import Item, Field


class ErfMeta(Item):
    gtin = Field()
