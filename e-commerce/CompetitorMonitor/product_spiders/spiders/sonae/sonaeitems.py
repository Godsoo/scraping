from scrapy.item import Item, Field


class SonaeMeta(Item):
    stock = Field()
    exclusive_online = Field()
    promotion_price = Field()
    delivery_24 = Field()  # Delivery in 24hrs
    delivery_24_48 = Field()  # Delivery 24 - 48hrs
    delivery_48_96 = Field()  # Delivery 48 - 96hrs
    delivery_96_more = Field()  # Delivery 96hrs or more
    ref_code = Field()
    promo_start = Field()
    promo_end = Field()
    extraction_timestamp = Field()
