# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ScccroselfservicescraperItem(scrapy.Item):
    url = scrapy.Field()
    DocumentType = scrapy.Field()
    DocumentNumber = scrapy.Field()
    RecordingDate = scrapy.Field()
    NumberPages = scrapy.Field()
    Grantor = scrapy.Field()
    Grantee = scrapy.Field()
    APN = scrapy.Field()
