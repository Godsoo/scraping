import os
import csv
from scrapy.spider import BaseSpider

from product_spiders.items import Product, ProductLoaderWithNameStrip as ProductLoader

from cStringIO import StringIO

from micheldeveritems import MicheldeverMeta

HERE = os.path.abspath(os.path.dirname(__file__))


class MicheldeverSpider(BaseSpider):
    name = 'micheldever-micheldever.co.uk'

    lego_filename = os.path.join(HERE, 'micheldever_products.csv')
    start_urls = ('http://app.competitormonitor.com/download_report?filename=micheldever_prices.csv',)
    allowed_domains = ['competitormonitor.com']

    def parse(self, response):
        fname = os.path.join(HERE, 'protyre1.csv')
        f = open(fname, 'w')
        f.write(response.body)
        f.close()

        protyre_prices = {}
        with open(fname) as f:
            p_reader = csv.DictReader(f)
            code_col = ''
            price_col = ''
            for c in p_reader.fieldnames:
                if c.lower() == 'code':
                    code_col = c
                elif c.lower() == 'price':
                    price_col = c

            for row in p_reader:
                protyre_prices[row[code_col].lower()] = row[price_col] if not row[price_col].startswith('#') else '0'

        f = open(os.path.join(HERE, 'micheldever_products.csv'))
        reader = csv.DictReader(f)
        for row in reader:
            loader = ProductLoader(response=response, item=Product())
            loader.add_value('identifier', row['MTS Stockcode'].lower())
            loader.add_value('sku', row['Ranking'])
            loader.add_value('brand', row['Brand'])
            loader.add_value('category', row['Segment'].decode('utf8'))
            loader.add_value('name', row['Description'].decode('utf8'))
            loader.add_value('price', protyre_prices.get(row['MTS Stockcode'].lower()) or row['Portsmouth POD1 Price'])
            item = loader.load_item()

            metadata = MicheldeverMeta()
            metadata['mts_stock_code'] = row['MTS Stockcode']
            metadata['full_tyre_size'] = row['Full Tyre Size']
            metadata['width'] = row['Width']
            metadata['aspect_ratio'] = row['Aspect Ratio']
            metadata['rim'] = row['Rim']
            metadata['load_rating'] = row['Load rating']
            metadata['speed_rating'] = row['Speed rating']
            metadata['alternative_speed_rating'] = row['Alt Speed']
            metadata['x_load'] = row['XLOAD']
            metadata['run_flat'] = row['Run Flat']
            metadata['manufacturer_mark'] = row['Manuf mark']
            metadata['pattern'] = row['Pattern']
            metadata['ip_code'] = row['IP code']
            metadata['tyre_label_fuel'] = row['Tyre Label Fuel']
            metadata['tyre_label_wet_grip'] = row['Tyre Lable Wet grip']
            metadata['tyre_label_noise'] = row['tyre Label Noise']
            metadata['pg'] = row['PG']
            metadata['pop'] = row['POP']
            metadata['comments'] = row['Comments']

            item['metadata'] = metadata
            yield item




