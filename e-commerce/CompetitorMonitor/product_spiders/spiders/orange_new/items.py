# -*- coding: utf-8 -*-

from scrapy.item import Item, Field
from scrapy.contrib.loader import ItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst
from scrapy.utils.markup import remove_entities

from product_spiders.utils import extract_price

class OrangeNewMeta(Item):
    device_name = Field()
    device_identifier = Field()
    plan_name = Field()
    period = Field()
    one_time_charge = Field()
    per_month = Field()
    operator = Field()
    channel = Field()
    category = Field()
    network_gen = Field()

class OrangeNewMetaLoader(ItemLoader):
    device_name_in = MapCompose(unicode, unicode.strip, remove_entities)
    device_name_out = Join()

    plan_name_in = MapCompose(unicode, unicode.strip, remove_entities)
    plan_name_out = Join()

    one_time_charge_in = MapCompose(unicode, unicode.strip, extract_price)
    one_time_charge_out = TakeFirst()

    per_month_in = MapCompose(unicode, unicode.strip, extract_price)
    per_month_out = TakeFirst()

    category_in = MapCompose(unicode, unicode.strip)
    category_out = TakeFirst()

    channel_in = MapCompose(unicode, unicode.strip)
    channel_out = TakeFirst()

    operator_in = MapCompose(unicode, unicode.strip)
    operator_out = TakeFirst()

    period_in = MapCompose(int)
    period_out = TakeFirst()

    network_gen_in = MapCompose(unicode)
    network_gen_out = TakeFirst()

    device_identifier_in = MapCompose(unicode)
    device_identifier_out = TakeFirst()