from scrapy.item import Item, Field

class SupplementMeta(Item):
    list_price = Field()
    item_variant = Field()