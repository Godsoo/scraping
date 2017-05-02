# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Inmuebles24Item(scrapy.Item):
    # define the fields for your item here like:
    mycity   = scrapy.Field()
    title    = scrapy.Field()
    price    = scrapy.Field()
    comment  = scrapy.Field()
    detail   = scrapy.Field()
    entrega  = scrapy.Field()
    unidades = scrapy.Field()
    metros   = scrapy.Field()
    banos    = scrapy.Field()
    m2totales    = scrapy.Field()
    habitaciones = scrapy.Field()

    datos_principales = scrapy.Field()
    descripción = scrapy.Field()
    ambientes   = scrapy.Field()
    servicios   = scrapy.Field()
    ubicación   = scrapy.Field()
    exteriores  = scrapy.Field()
    generales   = scrapy.Field()
    areas_sociales = scrapy.Field()



class MetroscubicosItem(scrapy.Item):

    # title    = scrapy.Field()
    price    = scrapy.Field()
    offers   = scrapy.Field()
    address  = scrapy.Field()
    size     = scrapy.Field()
    rooms    = scrapy.Field()

    detail   = scrapy.Field()

    Ubicación    = scrapy.Field()
    Descripción  = scrapy.Field()
    Ambientes    = scrapy.Field()
    Comodidades  = scrapy.Field()
    Desc_title   = scrapy.Field()
    Desc_content = scrapy.Field()


