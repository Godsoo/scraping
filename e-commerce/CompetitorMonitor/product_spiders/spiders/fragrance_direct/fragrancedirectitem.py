from scrapy.item import Item, Field

class FragranceDirectMeta(Item):
    promotional_data = Field()
    promotion = Field()
    rrp = Field()
    cost_price = Field()
    ean = Field()
    price_on_site = Field()
    minimum_sell = Field()
    price_exc_vat = Field()
    cost_price_exc_vat = Field()