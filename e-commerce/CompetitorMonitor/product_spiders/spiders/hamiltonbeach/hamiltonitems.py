from datetime import date, datetime
import re

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst, Identity
from scrapy.utils.markup import remove_entities

from product_spiders.items import ProductLoaderWithNameStrip

class UnifiedBrand(object):

    replacements = [
        ('Babycakes', 'Baby Cakes'),
        ('Black &Decker', 'Black & Decker'),
        ('KitchenAid', 'Kitchen Aid'),
        ('Nutribullet', 'Nutri Bullet'),
        ('Proctor-Silex', 'Proctor Silex'),
        ('Tefal', 'T-Fal'),
        ('ninja', 'Ninja')]

    def __call__(self, values):
        j = Join()
        brand = j(values)
        for b, r in self.replacements:
            b_tmp = brand.replace(' ', '').replace('-', '').lower()
            r_tmp = r.replace(' ', '').replace('-', '').lower()
            if b_tmp == r_tmp or b.lower() == brand.lower():
                return r
        return brand

class ProductLoader(ProductLoaderWithNameStrip):
    brand_in = MapCompose(unicode, remove_entities)
    brand_out = UnifiedBrand()

class HamiltonMeta(Item):
    reviews = Field()
    brand = Field()

class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()

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
