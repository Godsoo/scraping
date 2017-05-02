import os
import csv
from scrapy import Spider
from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader
from product_spiders.utils import extract_price
from cStringIO import StringIO

HERE = os.path.abspath(os.path.dirname(__file__))


class InstantPrint(Spider):
    name = 'instantprint-instantprint.co.uk'

    main_filename = os.path.join(HERE, 'instantprint_products.csv')
    start_urls = ('file://' + main_filename,)

    def parse(self, response):
        reader = csv.DictReader(StringIO(response.body))
        for row in reader:
            product_price = extract_price(row['SalePrice'])
            if not product_price:
                product_price = extract_price(row['Price'])
            product_name = ' - '.join([
                row['PaperType'], row['LaminationType'], row['PrintType'],
                row['PaperSize'], row['FoldingType']])
            product_identifier = row['ProductID']
            if row['ProdRange'] != 'NULL':
                product_category = row['ProductType'] + ' - ' + row['ProdRange']
            else:
                product_category = row['ProductType']

            loader = ProductLoader(item=Product(), response=response)
            loader.add_value('name', product_name)
            loader.add_value('identifier', product_identifier)
            loader.add_value('sku', product_identifier)
            loader.add_value('price', product_price)
            loader.add_value('category', product_category)

            item = loader.load_item()
            item['metadata'] = row.copy()
            yield item
