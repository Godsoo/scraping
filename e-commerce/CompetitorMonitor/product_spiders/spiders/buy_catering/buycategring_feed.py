# -*- coding: utf-8 -*-
import os
import csv
from scrapy.spider import BaseSpider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class BuyCateringSpider(BaseSpider):
    name = 'buycatering-buycatering.com'

    start_urls = ['http://www.buycatering.com/buycatfeed.csv']

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row["Unique Product ID"])
            loader.add_value('sku', row["Product code"])
            loader.add_value('category', unicode(row["Category"].decode('ISO-8859-1')))
            loader.add_value('name', unicode(row["Product name"].decode('ISO-8859-1')))
            loader.add_value('price', row["Price"])
            loader.add_value('url', row["Product page URL"])
            loader.add_value('brand', unicode(row["Brand"].decode('ISO-8859-1')))
            loader.add_value('image_url', row['Image URL'])
            out_of_stock = row['Stock availability'].upper() != 'IN STOCK'
            if out_of_stock:
                loader.add_value('stock', 0)
            yield loader.load_item()
