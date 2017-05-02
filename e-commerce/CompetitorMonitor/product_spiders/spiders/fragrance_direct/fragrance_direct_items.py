# -*- coding: utf-8 -*-
from scrapy.item import Item, Field

class FragranceDirectMeta(Item):
    promotion = Field()
    price_exc_vat = Field()