# -*- coding: utf-8 -*-
import csv
import os
import sys
import re
from itertools import chain

HERE = os.path.abspath(os.path.dirname(__file__))
spiders_root = os.path.dirname(HERE)
product_spiders_root = os.path.dirname(spiders_root)
project_spiders_root = os.path.dirname(product_spiders_root)

sys.path.append(product_spiders_root)
sys.path.append(project_spiders_root)

import click

main_filename = 'manual_mtsstockcodes.csv'

from asdatyes import AsdaTyresSpider
from bestbuytyres import BestBuyTyresSpider
from blackcircles_spider import BlackcirclesSpider
from camskill_spider import CamSkillSpider
from cartyres import CarTyresSpider
from etyres import EtyresSpider
from eventtyres_spider import EvenTyresSpider
from f1autocentres import EtyresSpider as F1AutoCentres
from halfords import HalfordsSpider
from kwikfit_spider import KwikFitSpider
from lovetyres import LoveTyresSpider
from mytyres import MyTyresSpider
from oponeo import OponeoSpider
from pneusonline import TyresPneusOnlineSpider
from tyrebookers import TyrebookersSpider
from tyredrive import TyreDriveSpider
from tyregiant_spider import TyreGiantSpider
from tyreleader import TyreleaderSpider
from tyresavings_spider import TyresavingsSpider
from tyreshopper import TyreShopperSpider
from tyresonthedrive_spider import TyresOnTheDriveSpider
from tyretraders import TyreTradersSpider
from valuetyres import ValueTyresSpider

from micheldeverutils import find_brand_segment

websites_mapping = {
    'AsdaTyres': AsdaTyresSpider.name,
    'BestBuyTyres': BestBuyTyresSpider.name,
    'BlackCircles': BlackcirclesSpider.name,
    'Camskill': CamSkillSpider.name,
    'CarTyres': CarTyresSpider.name,
    'Etyres': EtyresSpider.name,
    'EventTyres': EvenTyresSpider.name,
    'F1Autocentres': F1AutoCentres.name,
    'Halfords': HalfordsSpider.name,
    'Kwik-Fit': KwikFitSpider.name,
    'LoveTyres': LoveTyresSpider.name,
    'MyTyres': MyTyresSpider.name,
    'Oponeo': OponeoSpider.name,
    'Pneus': TyresPneusOnlineSpider.name,
    'TyreBookers': TyrebookersSpider.name,
    'Tyredrive': TyreDriveSpider.name,
    'TyreGiant': TyreGiantSpider.name,
    'TyreLeader': TyreleaderSpider.name,
    'TyreSavings': TyresavingsSpider.name,
    'TyreShopper': TyreShopperSpider.name,
    'TyresOnTheD': TyresOnTheDriveSpider.name,
    'TyreTraders': TyreTradersSpider.name,
    'ValueTyres': ValueTyresSpider.name,
}

class WebsiteNotFound(Exception):
    pass

def get_key(row):
    key = "%(Website)s-%(Width)s-%(Aspect Ratio)s-%(Rim)s-%(Speed Rating)s-%(Alternative speed rating)s-" \
          "%(Load rating)s-%(XL)s-%(Run Flat)s-%(Brand)s-%(Pattern)s-%(Manufacturer mark)s" % row
    return key

mts_code_regex1 = re.compile(r'(?P<width>\d{3})(?P<aspect_ratio>\d{2})(?P<rim>\d{2})', re.I)
mts_code_regex2 = re.compile(r'(?P<width>\d{3})(?P<rim>\d{2})', re.I)

def get_tyre_size_from_mts_code(mts_code):
    """
    >>> get_tyre_size_from_mts_code("2454018ZBRRE050R")
    ('245', '40', '18')
    >>> get_tyre_size_from_mts_code("15513TBUEN726")
    ('155', None, '13')
    """
    m = mts_code_regex1.search(mts_code)
    if m:
        res = m.groupdict()
        return (
            res['width'],
            res['aspect_ratio'],
            res['rim']
        )
    m = mts_code_regex2.search(mts_code)
    if m:
        res = m.groupdict()
        return (
            res['width'],
            None,
            res['rim']
        )
    return (None, None, None)

def preprocess_products(products, new_products):
    all_products = []
    processed = {}
    for product in chain(new_products, products):
        for field, value in product.items():
            product[field] = value.strip()
        if product['Website'] in websites_mapping.values():
            pass
        elif not product['Website'] in websites_mapping:
            raise WebsiteNotFound("Website '%s' not found in mapping" % product['Website'])
        else:
            product['Website'] = websites_mapping[product['Website']]

        product['Brand'] = product['Brand'].title()

        if not product['XL']:
            product['XL'] = 'No'
        elif product['XL'] == 'XL':
            product['XL'] = 'Yes'

        if not product['Run Flat']:
            product['Run Flat'] = 'No'
        elif product['Run Flat'] == 'RFT':
            product['Run Flat'] = 'Yes'

        if product['Segment'] == 'premiumbrands':
            product['Segment'] = 'Premium Brands'
        if product['Segment'] == 'housebrands':
            product['Segment'] = 'House Brands'

        if not product['Segment']:
            product['Segment'] = find_brand_segment(product['Brand'])

        key = get_key(product)
        if key in processed:
            # print "Duplicate: %s" % key
            if processed[key] != product['MTS Stock Code']:
                print "Duplicate product with different MTS Code: %s. Code1: %s, code2: %s" % (
                    key,
                    processed[key],
                    product['MTS Stock Code']
                )
            continue
        processed[key] = product['MTS Stock Code']

        if product['MTS Stock Code']:
            # check MTS code is correct for current tyre size
            width, aspect_ratio, rim = get_tyre_size_from_mts_code(product['MTS Stock Code'])
            if width and width != product['Width']:
                print "Record has incorrect width for MTS code '%s', width: %s, code width: %s" % (
                    product['MTS Stock Code'],
                    product['Width'],
                    width
                )
                continue
            if aspect_ratio and aspect_ratio != product['Aspect Ratio']:
                print "Record has incorrect Aspect Ratio for MTS code '%s', Aspect Ratio: %s, code Aspect Ratio: %s" % (
                    product['MTS Stock Code'],
                    product['Aspect Ratio'],
                    aspect_ratio
                )
                continue
            if rim and rim != product['Rim']:
                print "Record has incorrect rim for MTS code '%s', rim: %s, code rim: %s" % (
                    product['MTS Stock Code'],
                    product['Rim'],
                    rim
                )
                continue
            all_products.append(product)
    return all_products

def get_products(filename):
    if os.path.exists(filename):
        return list(csv.DictReader(open(filename)))
    else:
        return []

def save_products(filename, products):
    fields = [
        'MTS Stock Code',
        'Website',
        'Pattern',
        'Brand',
        'Segment',
        'Full Tyre Size',
        'Width',
        'Aspect Ratio',
        'Rim',
        'Load rating',
        'Speed Rating',
        'Alternative speed rating',
        'XL',
        'Run Flat',
        'Manufacturer mark',
        'Fitted or Delivered',
        'Price',
    ]
    products.sort(key=lambda x: (x['Website'], x['Brand'], x['Width'], x['Aspect Ratio'], x['Rim'], x['Load rating'],
                                 x['Speed Rating'], x['Alternative speed rating'], x['XL'], x['Run Flat'], x['Pattern'],
                                 x['MTS Stock Code']))
    if os.path.exists(filename):
        f = open(filename, 'w+')
    else:
        f = open(filename, 'a+')
    writer = csv.DictWriter(f, fields)
    writer.writeheader()
    writer.writerows(products)
    f.close()

@click.command()
@click.argument('filename')
def main(filename):
    if not os.path.exists(filename):
        click.echo("Error: file does not exist: %s" % filename)
        exit(1)
    main_products = get_products(main_filename)
    new_products = get_products(filename)
    if not new_products:
        click.echo("Error: no products found in file: %s" % filename)
        exit(1)

    products = preprocess_products(main_products, new_products)

    save_products(main_filename, products)

if __name__ == "__main__":
    main()