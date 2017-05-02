# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ArticleItem(scrapy.Item):

	title  = scrapy.Field()
	desc   = scrapy.Field()
	author = scrapy.Field()
	detail   = scrapy.Field()


class YellowscraperItem(scrapy.Item):

    link       = scrapy.Field()
    name       = scrapy.Field()
    alt_name   = scrapy.Field()
    address    = scrapy.Field()
    phone_main = scrapy.Field()
    about      = scrapy.Field()
    fax        = scrapy.Field()
    phone_addi = scrapy.Field()
    phone_mobi = scrapy.Field()
    email      = scrapy.Field()
    website    = scrapy.Field()
    prod_serv  = scrapy.Field()
    # busi_catg  = scrapy.Field()
    prim_catg  = scrapy.Field()
    othe_catg  = scrapy.Field()
    spec_feat  = scrapy.Field()
    tags       = scrapy.Field()
    articles   = scrapy.Field()

