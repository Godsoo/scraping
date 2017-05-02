from datetime import date, datetime
import re

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.utils.markup import remove_entities

class KeterMeta(Item):
    reviews = Field()
    brand = Field()
    
class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()
    product_url = Field()
    sku = Field()
    review_id = Field()

def extract_date(s, loader_context):
    date_format = loader_context['date_format']
    d = datetime.strptime(s, date_format)
    return d.strftime('%d/%m/%Y')

def extract_rating(s):
    r = re.search('(\d+)', s)
    if r:
        return int(r.groups()[0])

class ReviewLoader(XPathItemLoader):
    date_in = MapCompose(unicode, unicode.strip, extract_date, date_format='%d/%m/%Y')
    date_out = TakeFirst()
    
    rating_in = MapCompose(unicode, extract_rating)
    rating_out = TakeFirst()
    
    full_text_in = MapCompose(unicode, unicode.strip, remove_entities)
    full_text_out = Join()

    url_in = MapCompose(unicode, unicode.strip)
    url_out = TakeFirst()

    product_url_in = MapCompose(unicode, unicode.strip)
    product_url_out = TakeFirst()

    sku_in = MapCompose(unicode, unicode.strip, unicode.lower)
    sku_out = TakeFirst()
    
    review_id_in = MapCompose(unicode, unicode.strip)
    review_id_out = TakeFirst()