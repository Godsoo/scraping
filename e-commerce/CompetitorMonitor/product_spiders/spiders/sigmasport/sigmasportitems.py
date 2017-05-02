from datetime import date, datetime
from decimal import Decimal
import re

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.utils.markup import remove_entities

def extract_exc_vat_price(product):
    inc_vat_categories = ['Energy Food > EF Energy Gel', 
                          'Helmet > Helmet TT', 
                          'Helmet > Helmet Mens', 
                          'Helmet > Helmet Womens', 
                          'Helmet > Helmet Boys']

    if product['category'] in inc_vat_categories:
        return str(product['price'])
    else:
        return str(round(Decimal(product['price']) / Decimal(1.20), 2))

class SigmaSportMeta(Item):
    mpn = Field()
    item_group_number = Field()
    cost_price = Field()
    price_exc_vat = Field()
    sku_gb = Field()
