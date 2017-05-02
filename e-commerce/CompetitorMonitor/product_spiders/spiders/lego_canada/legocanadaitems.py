# -*- coding: utf-8 -*-

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.utils.markup import remove_entities


class LegoCanadaMeta(Item):
    on_shelf = Field()
    launch_date = Field()
    exit_date = Field()
    margin = Field()
