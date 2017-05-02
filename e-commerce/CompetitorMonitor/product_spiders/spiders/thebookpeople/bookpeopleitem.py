from datetime import date, datetime
import re

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.utils.markup import remove_entities

class BookpeopleMeta(Item):
    tbp_code = Field()
    uk_rrp = Field()
    feature = Field()
    pages = Field()
    author = Field()
    quantity = Field()
    cost_price = Field()
    
