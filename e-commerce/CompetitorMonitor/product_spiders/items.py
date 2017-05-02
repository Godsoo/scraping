# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/topics/items.html
from decimal import Decimal

from scrapy.item import Item, Field

from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity

from scrapy.utils.markup import remove_entities

from utils import extract_price, extract_price_eu, fix_spaces

class Product(Item):
    identifier = Field(default='')
    url = Field()
    name = Field()
    price = Field(default=Decimal(0))
    sku = Field(default='')
    metadata = Field()
    category = Field(default='')
    image_url = Field(default='')
    brand = Field(default='')
    shipping_cost = Field(default=Decimal(0))
    stock = Field(default='')
    dealer = Field(default='')

class ProductLoader(XPathItemLoader):
    identifier_in = MapCompose(unicode, unicode.strip)
    identifier_out = TakeFirst()

    url_out = TakeFirst()

    name_in = MapCompose(unicode, remove_entities, unicode.strip)
    name_out = Join()

    price_in = MapCompose(unicode, unicode.strip, extract_price)
    price_out = TakeFirst()

    sku_in = MapCompose(unicode, unicode.strip, unicode.lower)
    sku_out = TakeFirst()

    category_in = MapCompose(unicode, remove_entities)
    category_out = Join(" > ")

    image_url_out = TakeFirst()

    brand_in = MapCompose(unicode, remove_entities)
    brand_out = Join()

    shipping_cost_in = MapCompose(unicode, unicode.strip, extract_price)
    shipping_cost_out = TakeFirst()

    stock_in = MapCompose(unicode, unicode.strip, int, unicode)
    stock_out = TakeFirst()

    dealer_in = MapCompose(unicode, remove_entities)
    dealer_out = Join()

class ProductLoaderEU(ProductLoader):

    price_in = MapCompose(unicode, unicode.strip, extract_price_eu)
    price_out = TakeFirst()

class ProductLoaderWithNameStrip(ProductLoader):
    name_in = MapCompose(ProductLoader.name_in, unicode.strip)
    
class ProductLoaderWithNameStripEU(ProductLoaderWithNameStrip):
    price_in = MapCompose(unicode, unicode.strip, extract_price_eu)

class ProductLoaderWithoutSpaces(ProductLoaderWithNameStrip):
    name_in = MapCompose(ProductLoaderWithNameStrip.name_in, fix_spaces)
    category_in = MapCompose(ProductLoaderWithNameStrip.name_in, fix_spaces)
    brand_in = MapCompose(ProductLoaderWithNameStrip.name_in, fix_spaces)

class ProductLoaderWithoutSpacesEU(ProductLoaderWithoutSpaces):
    price_in = MapCompose(unicode, unicode.strip, extract_price_eu)    
