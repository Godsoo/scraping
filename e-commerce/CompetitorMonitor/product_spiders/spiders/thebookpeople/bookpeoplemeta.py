from scrapy.item import Item, Field


class BookpeopleMeta(Item):
    pre_order = Field()
    author = Field()
    format = Field()
    publisher = Field()
    published = Field()
