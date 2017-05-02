from scrapy.item import Item, Field

class KitBagMeta(Item):
    player = Field()
    number = Field()


