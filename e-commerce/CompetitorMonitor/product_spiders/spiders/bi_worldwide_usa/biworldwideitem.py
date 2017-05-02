from datetime import date, datetime
import re

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.utils.markup import remove_entities

class BIWordlwideMeta(Item):
    dropship_fee = Field()
    est_tax = Field()
    ship_weight = Field()
    product_group = Field()
    upc = Field()
    mpn = Field()
    item_group = Field()
    bi_tag_1 = Field()
    bi_tag_2 = Field()

