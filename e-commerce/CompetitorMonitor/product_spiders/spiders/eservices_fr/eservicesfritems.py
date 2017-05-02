# -*- coding: utf-8 -*-
from datetime import date, datetime
import re

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.utils.markup import remove_entities


class EservicesFrMeta(Item):
    mpn = Field()
