# -*- coding: utf-8 -*-
from scrapy.item import Item, Field


class PowerTools2uMeta(Item):
    part_number = Field()
    warranty = Field()



