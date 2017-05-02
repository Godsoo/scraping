import csv
import os

from scrapy.contrib.loader.processor import Compose, Join

from product_spiders.items import ProductLoaderWithNameStrip

here = os.path.abspath(os.path.dirname(__file__))
f = open(os.path.join(here, 'brandsmap.csv'))

reader = csv.DictReader(f)
BRAND_MAP = {}
for row in reader:
    if row['name'] not in BRAND_MAP:
        BRAND_MAP[row['name']] = {}

    BRAND_MAP[row['name']][row['old'].lower()] = row['new']

def replace_brand(s, loader_context):
    spider_name = loader_context.get('spider_name')
    brand_map = BRAND_MAP
    if spider_name in brand_map and s.lower() in brand_map[spider_name]:
        return brand_map[spider_name][s.lower()]
    else:
        return s

class TigerChefLoader(ProductLoaderWithNameStrip):
    brand_out = Compose(Join(), replace_brand)
