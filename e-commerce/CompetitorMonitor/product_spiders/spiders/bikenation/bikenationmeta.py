from scrapy.item import Item, Field


class BikeNationMeta(Item):
    stock_status = Field()
