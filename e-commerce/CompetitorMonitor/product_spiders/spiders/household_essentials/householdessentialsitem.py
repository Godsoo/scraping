from scrapy.item import Item, Field

class HouseholdEssentialsMeta(Item):
    amazon_asin = Field()
    target_tcin = Field()
    walmart_code = Field()
    wayfair_code = Field()
    upc = Field()
    reviews = Field()

class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()
