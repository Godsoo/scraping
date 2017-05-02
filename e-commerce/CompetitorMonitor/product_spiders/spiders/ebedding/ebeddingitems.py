# -*- coding: utf-8 -*-
from scrapy.item import Item, Field

class EbeddingMeta(Item):
    cost_price = Field()
    ean = Field()

