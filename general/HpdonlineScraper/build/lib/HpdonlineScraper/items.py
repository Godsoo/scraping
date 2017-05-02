# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class HpdonlinescraperItem(scrapy.Item):
	# for first table
    HPDsharp = scrapy.Field()
    Range = scrapy.Field()
    Block = scrapy.Field()
    Lot = scrapy.Field()
    CD = scrapy.Field()
    CensusTract = scrapy.Field()
    Stories = scrapy.Field()
    A_Units = scrapy.Field()
    B_Units = scrapy.Field()
    Ownership = scrapy.Field()
    Registrationsharp = scrapy.Field()
    Class = scrapy.Field()

    # for second table
    Owner = scrapy.Field()
    # LastReg_Expire = scrapy.Field()
    LastReg = scrapy.Field()
    RegExp = scrapy.Field()
    Organization = scrapy.Field()
    LastNm = scrapy.Field()
    FirstNm = scrapy.Field()
    HouseNo = scrapy.Field()
    StreetNm = scrapy.Field()
    Apt = scrapy.Field()
    City = scrapy.Field()
    State = scrapy.Field()
    Zip = scrapy.Field()
