# -*- coding: utf-8 -*-
import re

from scrapy.item import Item, Field
from scrapy.contrib.loader import XPathItemLoader
from scrapy.contrib.loader.processor import MapCompose, Join, TakeFirst
from scrapy.utils.markup import remove_entities

from product_spiders.items import Product, ProductLoaderWithNameStrip


def filter_name(name):
    m = re.search(r"^new offers for", name, re.I)
    if m:
        found = m.group(0)
        res = name.replace(found, "")
        res = res.strip()
    else:
        res = name
    if len(res) > 1024:
        res = res.strip()[:1021] + '...'
    return res

def filter_brand(brand):
    if len(brand) > 100:
        brand = brand.strip()[:97] + '...'
    return brand


class AmazonProduct(Product):
    pass


class AmazonProductLoader(ProductLoaderWithNameStrip):
    """
    >>> from scrapy.selector import HtmlXPathSelector
    >>> selector = HtmlXPathSelector(text="<html></html>")
    >>> loader = AmazonProductLoader(Product(), selector=selector)
    >>> loader.add_value('name', 'new offers for Lego asd')
    >>> loader.get_output_value('name')
    u'Lego asd'
    >>> loader.add_value('brand', 'a' * 200)
    >>> res = loader.get_output_value('brand')
    >>> len(res)  # 100 symbols maximum
    100
    >>> res == u'a'*97 + '...'
    True
    """
    name_in = MapCompose(ProductLoaderWithNameStrip.name_in, unicode.strip, filter_name)
    brand_in = MapCompose(ProductLoaderWithNameStrip.brand_in, filter_brand)
    sku_in = MapCompose(unicode, unicode.strip, unicode.lower)


class Review(Item):
    date = Field()
    rating = Field()
    full_text = Field()
    url = Field()
    review_id = Field()
    author = Field()
    author_location = Field()

def extract_rating(s):
    r = re.search('(\d+)', s)
    if r:
        return int(r.groups()[0])

class ReviewLoader(XPathItemLoader):
    date_in = MapCompose(unicode, unicode.strip)
    date_out = TakeFirst()

    rating_in = MapCompose(unicode, extract_rating)
    rating_out = TakeFirst()

    full_text_in = MapCompose(unicode, unicode.strip, remove_entities)
    full_text_out = Join()

    url_in = MapCompose(unicode, unicode.strip)
    url_out = TakeFirst()

    product_url_in = MapCompose(unicode, unicode.strip)
    product_url_out = TakeFirst()

    review_id_in = MapCompose(unicode, unicode.strip, unicode.lower)
    review_id_out = TakeFirst()

    author_in = MapCompose(unicode, unicode.strip)
    author_out = TakeFirst()

    author_location_in = MapCompose(unicode, unicode.strip)
    author_location_out = TakeFirst()


class AmazonMeta(Item):
    reviews = Field()
    brand = Field()
    universal_identifier = Field()