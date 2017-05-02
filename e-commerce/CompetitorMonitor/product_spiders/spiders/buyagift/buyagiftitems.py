# -*- coding: utf-8 -*-
from scrapy.item import Item, Field

class BuyAGiftMeta(Item):
    supplier_name = Field()
    summary = Field()
