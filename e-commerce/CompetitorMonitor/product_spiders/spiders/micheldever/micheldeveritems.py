# -*- coding: utf-8 -*-
from scrapy.item import Item, Field

class MicheldeverMeta(Item):
    sold_as = Field()
    aspect_ratio = Field()
    rim = Field()
    speed_rating = Field()
    width = Field()
    full_tyre_size = Field()
    load_rating = Field()
    alternative_speed_rating = Field()
    xl = Field()
    run_flat = Field()
    manufacturer_mark = Field()
    fitting_method  = Field()
    mts_stock_code = Field()
    onsite_name = Field()
    fuel = Field()
    grip = Field()
    noise = Field()
    # micheldever fields
    x_load = Field()
    pattern = Field()
    ip_code = Field()
    tyre_label_fuel = Field()
    tyre_label_wet_grip = Field()
    tyre_label_noise = Field()
    pg = Field()
    pop = Field()
    comments = Field()
