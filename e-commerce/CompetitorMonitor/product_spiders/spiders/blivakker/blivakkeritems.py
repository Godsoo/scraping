# -*- coding: utf-8 -*-
from scrapy.item import Item, Field


class BlivakkerMeta(Item):
    sku = Field()
    cost_price = Field()
    SalesPrice = Field()



