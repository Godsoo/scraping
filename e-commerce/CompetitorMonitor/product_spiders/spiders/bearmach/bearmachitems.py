# -*- coding: utf-8 -*-
import re

from scrapy.item import Item, Field


class BearmachMeta(Item):
    supplier_code = Field()
    supplier_name = Field()
    cost_price = Field()
