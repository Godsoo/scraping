# -*- coding: utf-8 -*-
import re

from scrapy.item import Item, Field


class OneStopBedroomsMeta(Item):
    coleman_sku = Field()
    coleman_url = Field()

