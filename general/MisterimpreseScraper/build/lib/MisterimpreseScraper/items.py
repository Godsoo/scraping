# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class MisterimpresescraperItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass

class CompanyItem(scrapy.Item):
    RAG1 = scrapy.Field()
    RAG2 = scrapy.Field()
    COMUNE = scrapy.Field()
    PROVINCIA = scrapy.Field()
    REGIONE = scrapy.Field()
    CATEGORIA = scrapy.Field()
    INDIRIZZO = scrapy.Field()
    CAP = scrapy.Field()
    CITTA = scrapy.Field()
    CONTATTI_01 = scrapy.Field()
    CONTATTI_02 = scrapy.Field()
    CONTATTI_03 = scrapy.Field()
    CONTATTI_04 = scrapy.Field()
    CONTATTI_05 = scrapy.Field()
    PIVA = scrapy.Field()
    # file_urls = scrapy.Field()
    # files = scrapy.Field()