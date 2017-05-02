# -*- coding: utf-8 -*-
from scrapy.item import Item, Field


class PowerhouseFitnessMeta(Item):
    discount_text = Field()
    discount_price = Field()
