from scrapy.item import Item, Field
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from decimal import Decimal


from scrapy import log

class FindelMeta(Item):
    cost_price = Field()
    


