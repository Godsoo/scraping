# -*- coding: utf-8 -*-
from scrapy.item import Item, Field

class LakelandMeta(Item):
    promotion = Field()
    promotional_message = Field()
    buyer_name = Field()
    list_price = Field()
    cost_price = Field()
    asin = Field()
    rrp = Field()
    margin = Field()
    dd = Field()
