# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class CercaziendescraperItem(scrapy.Item):
	pass

class CompanyItem(scrapy.Item):
    CATEGORIA = scrapy.Field()
    RAGIONE_SOCIALE = scrapy.Field()
    INDIRIZZO = scrapy.Field()
    CAP = scrapy.Field()
    COMUNE = scrapy.Field()
    PROVINCIA = scrapy.Field()
    TELEFONO = scrapy.Field()
    FAX = scrapy.Field()
    EMAIL = scrapy.Field()
    WEBSITE = scrapy.Field()
