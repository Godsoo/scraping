from datetime import date, datetime
import re

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.utils.markup import remove_entities

class TelecomsMeta(Item):
    monthly_cost = Field()
    tariff_name = Field()
    contract_duration = Field()
    operator = Field()
    channel = Field()
    network_generation = Field()
    device_name = Field()
    
