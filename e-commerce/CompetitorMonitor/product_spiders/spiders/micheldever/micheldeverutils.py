# -*- coding: utf-8 -*-
import logging
import os.path
import csv
import re
from difflib import SequenceMatcher
from collections import defaultdict

from product_spiders.base_spiders.matcher import Matcher

HERE = os.path.abspath(os.path.dirname(__file__))

def cache(fn):
    cache = {}

    def new_fn(*args):
        key = "".join([str(x) for x in args])
        if not key in cache:
            cache[key] = fn(*args)
        return cache[key]
    return new_fn

def fix_spaces(s):
    return " ".join(s.split())

@cache
def load_premium_brands():
    filename = os.path.join(HERE, 'premium_brands.csv')
    brands = [x['brand'] for x in csv.DictReader(open(filename))]
    return brands

@cache
def load_home_brands():
    filename = os.path.join(HERE, 'home_brands.csv')
    brands_grid = {x['brand']: x for x in csv.DictReader(open(filename))}
    for key, value in brands_grid.items():
        del(value['brand'])
    return brands_grid

@cache
def load_brand_synonyms():
    filename = os.path.join(HERE, 'brand_synonyms.csv')
    brands = {}
    for row in csv.DictReader(open(filename)):
        for field, value in row.items():
            brands[value] = row['brand']
    return brands

@cache
def load_mts_stock_codes():
    filename = os.path.join(HERE, 'mtsstockcodes.csv')
    mts_stock_codes = [x for x in csv.DictReader(open(filename))]
    return mts_stock_codes

@cache
def load_manual_mts_stock_codes():
    filename = os.path.join(HERE, 'manual_mtsstockcodes.csv')
    mts_stock_codes = [x for x in csv.DictReader(open(filename))]
    return mts_stock_codes

@cache
def load_manufacturers_marks():
    filename = os.path.join(HERE, 'manmarks.csv')
    man_marks = {x['code']: x['manufacturer_mark'] for x in csv.DictReader(open(filename))}
    return man_marks

@cache
def load_ip_codes_data():
    filename = os.path.join(HERE, 'ip_codes.csv')
    ip_codes_data = {x['IP CODE']: x for x in csv.DictReader(open(filename))}
    return ip_codes_data

@cache
def load_ean_codes_data():
    filename = os.path.join(HERE, 'ip_codes.csv')
    ean_codes_data = {x['EAN']: x for x in csv.DictReader(open(filename))}
    return ean_codes_data

def is_brand_correct(product_brand, matching_brand):
    """
    >>> is_brand_correct('bridgestone', 'bridgestone')
    True
    >>> is_brand_correct('bridgestone', 'yokohama')
    False
    >>> is_brand_correct('general tyre', 'yokohama')
    True
    >>> is_brand_correct('avon', 'yokohama')
    False
    >>> is_brand_correct('primewell', 'gt radial')
    True
    >>> is_brand_correct('toyo', 'gt radial')
    False
    >>> is_brand_correct('imagined brand', 'gt radial')
    False
    >>> is_brand_correct('imagined brand', 'avon')
    False
    >>> is_brand_correct('avon', 'avon')
    True
    >>> is_brand_correct('avon', 'falken')
    True
    >>> is_brand_correct('falken', 'avon')
    True
    >>> is_brand_correct('Falken', 'Avon')
    True
    >>> is_brand_correct('primewell', 'primewell')
    True
    >>> is_brand_correct('enduro', 'Runway')
    True
    >>> is_brand_correct('runway', 'Runway')
    True
    >>> is_brand_correct('Runway', 'runway')
    True
    """
    premium = False
    product_brand = unify_brand(product_brand)
    product_brand = product_brand.lower()
    matching_brand = unify_brand(matching_brand)
    matching_brand = matching_brand.lower()

    if product_brand == matching_brand:
        return True

    premium_brands = load_premium_brands()
    if matching_brand in premium_brands:
        premium = True
    if premium:
        if product_brand == matching_brand:
            return True
        else:
            return False

    home_brands_grid = load_home_brands()
    for main_brand, secondary_brands in home_brands_grid.items():
        if matching_brand == main_brand:
            if product_brand in secondary_brands and secondary_brands[product_brand]:
                return True

        if product_brand == main_brand:
            if matching_brand in secondary_brands and secondary_brands[matching_brand]:
                return True

    return False

def find_brand_segment(brand):
    if not brand:
        return 'House Brands'
    brand = brand.lower()
    premium_brands = load_premium_brands()
    if brand in premium_brands:
        return 'Premium Brands'
    else:
        return 'House Brands'

def unify_brand(brand):
    """
    >>> unify_brand("GT Radial")
    'GT'
    >>> unify_brand("Pirelli")
    'Pirelli'
    >>> unify_brand("Enduro")
    'Runway'
    """
    brand_synonyms = load_brand_synonyms()
    for synonym, main_brand in brand_synonyms.items():
        if brand.lower() == synonym.lower():
            return main_brand
    return brand

def is_product_correct(product):
    """
    >>> from decimal import Decimal
    >>> product = {'brand': u'Kumho',\
    'category': u'House Brands',\
    'identifier': u'11179484-Delivered',\
    'image_url': 'http://www.blackcircles.com/wso/images/library/obj16003867?view=2885',\
    'name': u'Ecsta SPT KU31',\
    'price': Decimal('51.804'),\
    'sku': u'2055516v',\
    'url': 'http://www.blackcircles.com/kumho/ku31/205/55/R16/V/91',\
    'metadata': {'alternative_speed_rating': '',\
    'aspect_ratio': '55',\
    'fitting_method': 'Delivered',\
    'full_tyre_size': u'205/55/16/91/V',\
    'load_rating': u'91',\
    'manufacturer_mark': '',\
    'mts_stock_code': '',\
    'rim': '16',\
    'run_flat': 'No',\
    'speed_rating': u'V',\
    'width': '205',\
    'xl': 'No'}}
    >>> is_product_correct(product)
    True
    """
    tyres_list = load_mts_stock_codes()
    metadata = product['metadata']
    for tyre in tyres_list:
        load_ratings = tyre['Load rating'].split('/')
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed rating'] or metadata['speed_rating'] == tyre['Alt Speed']) and
                  metadata['load_rating'] in load_ratings)

        xl_correct = (metadata['xl'] == "Yes" and tyre['XL'] == "XL") or (metadata['xl'] == "No" and tyre['XL'] == "")
        rf_correct = (metadata['run_flat'] == "Yes" and tyre['Run Flat'] == "RF") or (metadata['run_flat'] == "No" and tyre['Run Flat'] == "")

        brand_correct = is_brand_correct(tyre['Brand'], product['brand'].lower())
        # collect all Apollo tyres
        brand_is_apollo = product['brand'].lower() == 'apollo' or product['brand'].lower() == 'apollo tyres' or product['brand'].lower() == 'apollo tyre'
        brand_correct = brand_correct or brand_is_apollo
        if search and xl_correct and rf_correct and brand_correct:
            return True

    return False

def get_speed_rating(product):
    tyres_list = load_mts_stock_codes()
    manual_tyres_list = load_manual_mts_stock_codes()

    metadata = product['metadata']
    if metadata['mts_stock_code'].strip() and (metadata['mts_stock_code'].strip().lower() not in ('n/a', 'cwmf')) and \
       (not metadata['mts_stock_code'].strip().startswith('NS')):
        for tyre in tyres_list:
            if tyre['MTS Stockcode'] == metadata['mts_stock_code']:
                return tyre['Speed rating']
        for tyre in manual_tyres_list:
            if tyre['MTS Stock Code'] == metadata['mts_stock_code']:
                return tyre['Speed Rating']

    for tyre in tyres_list:
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed rating'] or metadata['speed_rating'] == tyre['Alt Speed']) and
                  metadata['load_rating'] == tyre['Load rating'])

        xl_correct = (metadata['xl'] == "Yes" and tyre['XL'] == "XL") or (metadata['xl'] == "No" and tyre['XL'] == "")
        rf_correct = (metadata['run_flat'] == "Yes" and tyre['Run Flat'] == "RF") or (metadata['run_flat'] == "No" and tyre['Run Flat'] == "")

        brand_correct = is_brand_correct(tyre['Brand'],
                                         product['brand'].lower())
        if search and xl_correct and rf_correct and brand_correct:
            return tyre['Speed rating']
    return metadata['speed_rating']

def get_alt_speed(product):
    tyres_list = load_mts_stock_codes()
    manual_tyres_list = load_manual_mts_stock_codes()

    metadata = product['metadata']
    if metadata['mts_stock_code'].strip() and (metadata['mts_stock_code'].strip().lower() not in ('n/a', 'cwmf')) and \
       (not metadata['mts_stock_code'].strip().startswith('NS')):
        for tyre in tyres_list:
            if tyre['MTS Stockcode'] == metadata['mts_stock_code']:
                return tyre['Alt Speed']
        for tyre in manual_tyres_list:
            if tyre['MTS Stock Code'] == metadata['mts_stock_code']:
                return tyre['Alternative speed rating']

    for tyre in tyres_list:
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed rating'] or metadata['speed_rating'] == tyre['Alt Speed']) and
                  metadata['load_rating'] == tyre['Load rating'])

        xl_correct = (metadata['xl'] == "Yes" and tyre['XL'] == "XL") or (metadata['xl'] == "No" and tyre['XL'] == "")
        rf_correct = (metadata['run_flat'] == "Yes" and tyre['Run Flat'] == "RF") or (metadata['run_flat'] == "No" and tyre['Run Flat'] == "")

        brand_correct = is_brand_correct(tyre['Brand'],
                                         product['brand'].lower())
        if search and xl_correct and rf_correct and brand_correct:
            return tyre['Alt Speed']
    return ''

def find_mts_stock_code(product, spider_name=None, log=None, ip_code=None, ean_code=None):
    """
    Searches for MTS stock code firstly in list of manually matched, then automatically using pattern matching
    :param product: product data, for which to search mts code
    :param spider_name: name of the spider (used in manual matching)
    :param log: log function to use when logging messages like "matched manually" or "matched automatically"
    :return: matching MTS stock code if found or empty string if not found

    >>> product = {\
        "brand": "Continental",\
        "category": "Premium Brands",\
        "identifier": "1620555VCOSPC2#",\
        "image_url": "http://www.asdatyres.co.uk/order/tyre_images/Continental/sportcontact2.jpg",\
        "metadata": {\
            "alternative_speed_rating": "",\
            "aspect_ratio": "55", \
            "fitting_method": "Fitted",\
            "full_tyre_size": "205/55/16/91/V",\
            "load_rating": "91",\
            "manufacturer_mark": "",\
            "rim": "16", \
            "run_flat": "No",\
            "speed_rating": "V",\
            "width": "205",\
            "xl": "No"\
        }, \
        "name": "Sport Contact 2",\
        "price": "77.80",\
        "sku": "",\
        "url": "http://asdatyres.co.uk"\
    }
    >>> find_mts_stock_code(product, spider_name='asdatyres.co.uk')
    '2055516VCOSPT2'
    >>> product = { \
        "brand": "Pirelli",  \
        "category": "Premium Brands",  \
        "identifier": "412554",  \
        "image_url": "http://cdn.tyreleader.co.uk/static/img/tyre_small_cp/7013.jpg",  \
        "metadata": { \
            "alternative_speed_rating": "",  \
            "aspect_ratio": "55",  \
            "fitting_method": "Delivered",  \
            "full_tyre_size": "205/55/16/91/V",  \
            "load_rating": "91",  \
            "manufacturer_mark": "", \
            "mts_stock_code": "2055516VPIP7CINT", \
            "rim": "16",  \
            "run_flat": "No", \
            "speed_rating": "V", \
            "width": "205",  \
            "xl": "No" \
        },  \
        "name": "Cinturato P7", \
        "price": "57.69",  \
        "sku": "",  \
        "url": "http://www.tyreleader.co.uk/car-tyres/pirelli/cinturato-p7/205-55-r16-91v-412554" \
    }
    >>> find_mts_stock_code(product, 'tyreleader.co.uk')
    '2055516VPIP7CINT'
    >>> product = { \
        "brand": "Pirelli",  \
        "category": "Premium Brands",  \
        "identifier": "412554",  \
        "image_url": "http://cdn.tyreleader.co.uk/static/img/tyre_small_cp/7013.jpg",  \
        "metadata": { \
            "alternative_speed_rating": "",  \
            "aspect_ratio": "55",  \
            "fitting_method": "Delivered",  \
            "full_tyre_size": "205/55/16/91/V",  \
            "load_rating": "91",  \
            "manufacturer_mark": "", \
            "mts_stock_code": "2055516VPIP7CINT", \
            "rim": "16",  \
            "run_flat": "No", \
            "speed_rating": "V", \
            "width": "205",  \
            "xl": "No" \
        },  \
        "name": "P7", \
        "price": "57.69",  \
        "sku": "",  \
        "url": "http://www.tyreleader.co.uk/car-tyres/pirelli/cinturato-p7/205-55-r16-91v-412554" \
    }
    >>> find_mts_stock_code(product, 'tyreleader.co.uk')
    '2055516VPIP7'
    >>> product = {\
        "brand": "Bridgestone",\
        "category": "Premium Brands",\
        "identifier": "1619555HBRER3002RFT",\
        "image_url": "http://www.asdatyres.co.uk/order/tyre_images/Bridgestone/er300.jpg",\
        "metadata": {\
            "alternative_speed_rating": "",\
            "aspect_ratio": "55", \
            "fitting_method": "Fitted",\
            "full_tyre_size": "195/55/16/87/H",\
            "load_rating": "87",\
            "manufacturer_mark": "",\
            "rim": "16",\
            "run_flat": "Yes",\
            "speed_rating": "H",\
            "width": "195",\
            "xl": "No"\
        },\
        "name": "ER300-2",\
        "price": "102.90",\
        "sku": "",\
        "url": "http://asdatyres.co.uk"\
    }
    >>> find_mts_stock_code(product, 'asdatyres.co.uk')
    '1955516HBRER300R'
    >>> product = {\
        "brand": "Pirelli",\
        "category": "House Brands",\
        "identifier": "pirelli-pzero-rosso-225-45-r17-91-w-mo",\
        "image_url": "http://www.oponeo.co.uk/Temp/pirelli-pzero-rosso-1285-t-f-l125-sk1.png",\
        "metadata": {\
            "alternative_speed_rating": "W",\
            "aspect_ratio": "45",\
            "fitting_method": "Delivered",\
            "full_tyre_size": "225/45/17/91/W",\
            "load_rating": "91",\
            "manufacturer_mark": "MO",\
            "mts_stock_code": "2254517ZPIPZROSS",\
            "rim": "17",\
            "run_flat": "No",\
            "speed_rating": "Z",\
            "width": "225",\
            "xl": "No"\
        },\
        "name": "PZero Rosso",\
        "price": "80",\
        "sku": "",\
        "url": "http://www.oponeo.co.uk/tyre-details/pirelli-pzero-rosso-225-45-r17-91-w"\
    }
    >>> find_mts_stock_code(product, 'oponeo.co.uk')
    '2254517ZPIROSSMO'
    >>> product = {\
        'brand': u'Pirelli',\
        'category': u'Premium Brands',\
        'identifier': u'100778',\
        'image_url': 'http://www.camskill.co.uk/smsimg/1943/100778--main--1943.jpg',\
        'metadata': {\
            u'alternative_speed_rating': '',\
            u'aspect_ratio': u'55',\
            u'fitting_method': u'Delivered',\
            u'full_tyre_size': u'205/55/16/91/V',\
            u'load_rating': u'91',\
            u'manufacturer_mark': None,\
            u'mts_stock_code': '2055516VPIP7',\
            u'rim': u'16',\
            u'run_flat': u'No',\
            u'speed_rating': 'V',\
            u'width': u'205',\
            u'xl': u'No'\
        },\
        'name': u'Cinturato P7',\
        'price': '61.90',\
        'sku': None,\
        'url': 'http://www.camskill.co.uk/m62b0s3986p100778/Pirelli_Tyres_Car_Pirelli_P7_Cinturato_Pirelli_P_7_-_205_55_R16_91V_%28MO%29_TL_Fuel_Eff_%3A_E_Wet_Grip%3A_B_NoiseClass%3A_2_Noise%3A_70dB'\
    }
    >>> find_mts_stock_code(product, 'micheldever-camskill.co.uk')
    '2055516VPIP7CINT'
    >>> product = {\
        'brand': u'Michelin',\
        'category': u'Premium Brands',\
        'identifier': u'102543',\
        'image_url': 'http://www.camskill.co.uk/smsimg/1127/102543-108166-main--1127.jpg',\
        'metadata': {\
            u'alternative_speed_rating': '',\
            u'aspect_ratio': u'55',\
            u'fitting_method': u'Delivered',\
            u'full_tyre_size': u'205/55/16/91/V',\
            u'load_rating': u'91',\
            u'manufacturer_mark': None,\
            u'mts_stock_code': '2055516VMIPRHPMO',\
            u'rim': u'16',\
            u'run_flat': u'No',\
            u'speed_rating': 'V',\
            u'width': u'205',\
            u'xl': u'No'\
        },\
        'name': u'Primacy HP',\
        'price': '66.50',\
        'sku': None,\
        'url': 'http://www.camskill.co.uk/m62b0s3986p102543/Michelin_Tyres_Car_Michelin_Primacy_HP_-_205_55_R16_91V_%28MO%29_TL_Fuel_Eff_%3A_C_Wet_Grip%3A_B_NoiseClass%3A_2_Noise%3A_70dB'\
    }
    >>> find_mts_stock_code(product, 'micheldever-camskill.co.uk')
    '2055516VMIPRIHPA'
    >>> product = {\
        'brand': u'Pirelli',\
        'category': u'Premium Brands',\
        'identifier': u'101375',\
        'image_url': 'http://www.camskill.co.uk/smsimg/1102/101375--main--1102.jpg',\
        'metadata': {\
            u'alternative_speed_rating': 'Y',\
            u'aspect_ratio': u'35',\
            u'fitting_method': u'Delivered',\
            u'full_tyre_size': u'235/35/19/91/Y',\
            u'load_rating': u'91',\
            u'manufacturer_mark': None,\
            u'mts_stock_code': '2353519ZPIPZERO1',\
            u'rim': u'19',\
            u'run_flat': u'No',\
            u'speed_rating': 'Z',\
            u'width': u'235',\
            u'xl': u'Yes'\
        },\
        'name': u'PZero',\
        'price': '156.40',\
        'sku': None,\
        'url': 'http://www.camskill.co.uk/m55b0s24p101375/Pirelli_Tyres_Car_Pirelli_PZero_Pirelli_P_Zero_-_235_35_R19_%2891Y%29_XL_%28L%29_TL_Fuel_Eff_%3A_E_Wet_Grip%3A_A_NoiseClass%3A_2_Noise%3A_72dB'
    }
    >>> find_mts_stock_code(product, 'micheldever-camskill.co.uk')
    '2353519ZPIPZERO'
    """
    product['name'] = product['name'].strip()
    if product['metadata']['manufacturer_mark'] is None:
        product['metadata']['manufacturer_mark'] = ''
    if ip_code is not None:
        mts_stock_code = find_mts_stock_code_by_ipcode(ip_code)
        if mts_stock_code:
            if log:
                log('MTS matched by IP Code %s: %s' % (ip_code, mts_stock_code))
            return mts_stock_code
    if ean_code is not None:
        mts_stock_code = find_mts_stock_code_by_ean(ean_code)
        if mts_stock_code:
            if log:
                log('MTS matched by EAN Code %s: %s' % (ean_code, mts_stock_code))
            return mts_stock_code
    mts_stock_code = find_manually_matched_mts_stock_code(product, spider_name=spider_name)
    if mts_stock_code:
        if log:
            log('MTS Manually matched: %s' % mts_stock_code)
        return mts_stock_code

    tyres_list = load_mts_stock_codes()
    metadata = product['metadata']
    for tyre in tyres_list:
        load_ratings = tyre['Load rating'].split('/')
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed rating'] or metadata['speed_rating'] == tyre['Alt Speed']) and
                  metadata['load_rating'] in load_ratings)

        xl_correct = (metadata['xl'] == "Yes" and tyre['XL'] == "XL") or (metadata['xl'] == "No" and tyre['XL'] == "")
        rf_correct = (metadata['run_flat'] == "Yes" and tyre['Run Flat'] == "RF") or (metadata['run_flat'] == "No" and tyre['Run Flat'] == "")

        brand_correct = is_brand_correct(tyre['Brand'],
                                         product['brand'].lower())
        if search and xl_correct and rf_correct and brand_correct:
            matched = tyre['Pattern'].lower().replace(' ', '') == product['name'].lower().replace(' ', '')
            if matched:
                if log:
                    log('MTS automatically matched: %s' % mts_stock_code)
                return tyre['MTS Stockcode']

    for tyre in tyres_list:
        load_ratings = tyre['Load rating'].split('/')
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed rating'] or metadata['speed_rating'] == tyre['Alt Speed']) and
                  metadata['load_rating'] in load_ratings)

        xl_correct = (metadata['xl'] == "Yes" and tyre['XL'] == "XL") or (metadata['xl'] == "No" and tyre['XL'] == "")
        rf_correct = (metadata['run_flat'] == "Yes" and tyre['Run Flat'] == "RF") or (metadata['run_flat'] == "No" and tyre['Run Flat'] == "")

        brand_correct = is_brand_correct(tyre['Brand'],
                                         product['brand'].lower())
        if search and xl_correct and rf_correct and brand_correct:
            matched = match_name(tyre['Pattern'], product['name']) or match_pattern(tyre['Pattern'], product['name'])
            if matched:
                if log:
                    log('MTS automatically matched: %s' % mts_stock_code)
                return tyre['MTS Stockcode']

    return ''

def find_mts_stock_code_by_ipcode(ip_code):
    ip_codes_data = load_ip_codes_data()
    if ip_code in ip_codes_data:
        return ip_codes_data[ip_code]['STCODE']
    return ''

def find_mts_stock_code_by_ean(ean_code):
    ean_codes_data = load_ean_codes_data()
    if ean_code in ean_codes_data:
        return ean_codes_data[ean_code]['STCODE']
    return ''

def find_manually_matched_mts_stock_code(product, spider_name=None, respect_website=True):
    """
    >>> product = { \
        "brand": "Falken", \
        "category": "House Brands", \
        "identifier": "32846300-Fitted", \
        "image_url": "http://www.blackcircles.com/wso/images/library/obj26189784?view=2885", \
        "metadata": { \
            "alternative_speed_rating": "", \
            "aspect_ratio": "70", \
            "fitting_method": "Fitted", \
            "full_tyre_size": "165/70/14/81/T", \
            "load_rating": "81", \
            "manufacturer_mark": "", \
            "mts_stock_code": "", \
            "rim": "14", \
            "run_flat": "No", \
            "speed_rating": "T", \
            "width": "165", \
            "xl": "No" \
        }, \
        "name": "Sincera SN832 Ecorun", \
        "price": "49.08", \
        "sku": "", \
        "url": "http://www.blackcircles.com/catalogue//falken/sincera-sn832-ecorun/165/70/R14/T/81" \
    }
    >>> find_manually_matched_mts_stock_code(product, 'blackcircles.com')
    '1657014TBUFA832'
    >>> product = { \
        "brand": "Pirelli",  \
        "category": "Premium Brands",  \
        "identifier": "412554",  \
        "image_url": "http://cdn.tyreleader.co.uk/static/img/tyre_small_cp/7013.jpg",  \
        "metadata": { \
            "alternative_speed_rating": "",  \
            "aspect_ratio": "55",  \
            "fitting_method": "Delivered",  \
            "full_tyre_size": "205/55/16/91/V",  \
            "load_rating": "91",  \
            "manufacturer_mark": "", \
            "mts_stock_code": "2055516VPIP7CINT", \
            "rim": "16",  \
            "run_flat": "No", \
            "speed_rating": "V", \
            "width": "205",  \
            "xl": "No" \
        },  \
        "name": "Cinturato P7", \
        "price": "57.69",  \
        "sku": "",  \
        "url": "http://www.tyreleader.co.uk/car-tyres/pirelli/cinturato-p7/205-55-r16-91v-412554" \
    }
    >>> find_manually_matched_mts_stock_code(product, 'tyreleader.co.uk')
    '2055516VPIP7CINT'
    >>> product = { \
        "brand": "Pirelli",  \
        "category": "Premium Brands",  \
        "identifier": "412554",  \
        "image_url": "http://cdn.tyreleader.co.uk/static/img/tyre_small_cp/7013.jpg",  \
        "metadata": { \
            "alternative_speed_rating": "",  \
            "aspect_ratio": "55",  \
            "fitting_method": "Delivered",  \
            "full_tyre_size": "205/55/16/91/V",  \
            "load_rating": "91",  \
            "manufacturer_mark": "", \
            "mts_stock_code": "2055516VPIP7CINT", \
            "rim": "16",  \
            "run_flat": "No", \
            "speed_rating": "V", \
            "width": "205",  \
            "xl": "No" \
        },  \
        "name": "P7", \
        "price": "57.69",  \
        "sku": "",  \
        "url": "http://www.tyreleader.co.uk/car-tyres/pirelli/cinturato-p7/205-55-r16-91v-412554" \
    }
    >>> find_manually_matched_mts_stock_code(product, 'tyreleader.co.uk')
    ''
    """
    if not spider_name and respect_website:
        return ''

    product['name'] = product['name'].strip()

    tyres_list = load_manual_mts_stock_codes()
    metadata = product['metadata']

    # first loop check for exact match
    for tyre in tyres_list:
        if tyre['Website'] != spider_name and respect_website:
            continue
        load_ratings = tyre['Load rating'].split('/')
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed Rating'] or metadata['speed_rating'] == tyre['Alternative speed rating']) and
                  metadata['load_rating'] in load_ratings)

        if not tyre['XL']:
            tyre['XL'] = 'No'
        if tyre['XL'] == 'XL':
            tyre['XL'] = 'Yes'
        if not tyre['Run Flat']:
            tyre['Run Flat'] = 'No'
        if tyre['Run Flat'] == 'RFT':
            tyre['Run Flat'] = 'Yes'

        xl_correct = (metadata['xl'] == tyre['XL'])
        rf_correct = (metadata['run_flat'] == tyre['Run Flat'])
        mf_mark_correct = (metadata['manufacturer_mark'] == tyre['Manufacturer mark'])

        brand_correct = is_brand_correct(tyre['Brand'],
                                         product['brand'].lower())
        if search and xl_correct and rf_correct and brand_correct and mf_mark_correct:
            matched = tyre['Pattern'].lower().replace(' ', '') == product['name'].lower().replace(' ', '')
            if matched:
                if tyre['MTS Stock Code']:
                    return tyre['MTS Stock Code']

    return ''

def find_man_mark(mark):
    """
    >>> find_man_mark('bmw')
    '*'
    >>> find_man_mark('Mercedes')
    'MO'
    >>> find_man_mark('por')
    'N0'
    """
    man_marks = load_manufacturers_marks()
    for code, manufacturer_mark in man_marks.items():
        if mark.lower() in code.lower():
            return manufacturer_mark
    return ''

matcher = Matcher(logging.error)

def match_name(search_name, new_item, match_threshold=90, important_words=None):
    r = matcher.match_ratio(search_name, new_item, important_words)
    return r >= match_threshold

def match_pattern(pattern, name, match_threshold=70):
    """
    >>> match_pattern('B 250 ECOPIA', 'B250ECO')
    True
    >>> match_pattern('DSPORT', 'Dueler Sport')
    True
    >>> match_pattern('4X4 CON', '4x4 Contact')
    True
    >>> match_pattern('Ranger HTT', 'GRABBER GT')
    False
    >>> match_pattern('CS2', 'CF2')
    False
    >>> match_pattern('RE040', 'RE002')
    False
    >>> match_pattern('ER300 RFT', 'ER300-2')
    False
    >>> match_pattern('ER300', 'ER300-2')
    False
    >>> match_pattern('BLUERESP', 'Bluresponse')
    True
    """
    # compare digits
    digits1 = "".join(re.findall(r"\d", pattern))
    digits2 = "".join(re.findall(r"\d", name))
    if digits1 != digits2:
        return False
    r = SequenceMatcher(None, pattern.lower().replace(' ', ''), name.lower().replace(' ', '')).ratio() * 100
    return r >= match_threshold

def is_run_flat(name):
    """
    >>> is_run_flat('RE050 - MOE')
    True
    >>> is_run_flat('Potenza RE050A')
    False
    >>> is_run_flat('POTENZA RE050  MO EXTENDED')
    True
    """
    if 'moe' in name.lower() or 'mo ext' in name.lower():
        return True
    return False


if __name__ == "__main__":
    import doctest
    doctest.testmod()

@cache
def load_mts_stock_codes_dict():
    filename = os.path.join(HERE, 'mtsstockcodes.csv')
    reader = csv.DictReader(open(filename))
    mts_stock_codes = defaultdict(list)
    for row in reader:
        key = get_mts_stock_key_from_csv(row)
        mts_stock_codes[key].append(row)

    return mts_stock_codes

def get_mts_stock_key_from_csv(row):
    keys = ['Width', 'Aspect Ratio', 'Rim' ,'XL' , 'Run Flat']
    return ':'.join([row[k] for k in keys])

def get_mts_stock_key(metadata):
    return '{}:{}:{}:{}:{}'.format(metadata['width'], metadata['aspect_ratio'],
                                   metadata['rim'], 'XL' if metadata['xl'] == 'Yes' else '',
                                   'RF' if metadata['run_flat'] == 'Yes' else '')

@cache
def load_manual_mts_stock_codes_dict():
    filename = os.path.join(HERE, 'manual_mtsstockcodes.csv')
    reader = csv.DictReader(open(filename))
    mts_stock_codes = defaultdict(list)
    for row in reader:
        if not row['XL'] or row['XL'] == 'No':
            row['XL'] = ''

        if not row['Run Flat'] or row['Run Flat'] == 'No':
            row['Run Flat'] = ''

        key = get_manual_mts_stock_key_from_csv(row)
        mts_stock_codes[key].append(row)

    return mts_stock_codes

def get_manual_mts_stock_key_from_csv(row):
    keys = ['Website', 'Width', 'Aspect Ratio', 'Rim' ,'XL' , 'Run Flat']
    return ':'.join([row[k] for k in keys])

def get_manual_mts_stock_key(website, metadata):
    return '{}:{}:{}:{}:{}:{}'.format(website, metadata['width'], metadata['aspect_ratio'],
                                   metadata['rim'], 'XL' if metadata['xl'] == 'Yes' else '',
                                   'RFT' if metadata['run_flat'] == 'Yes' else '')

def find_mts_stock_code_optimized(product, spider_name=None, log=None, ip_code=None):
    """
    Searches for MTS stock code firstly in list of manually matched, then automatically using pattern matching
    :param product: product data, for which to search mts code
    :param spider_name: name of the spider (used in manual matching)
    :param log: log function to use when logging messages like "matched manually" or "matched automatically"
    :return: matching MTS stock code if found or empty string if not found

    >>> product = {\
        "brand": "Continental",\
        "category": "Premium Brands",\
        "identifier": "1620555VCOSPC2#",\
        "image_url": "http://www.asdatyres.co.uk/order/tyre_images/Continental/sportcontact2.jpg",\
        "metadata": {\
            "alternative_speed_rating": "",\
            "aspect_ratio": "55", \
            "fitting_method": "Fitted",\
            "full_tyre_size": "205/55/16/91/V",\
            "load_rating": "91",\
            "manufacturer_mark": "",\
            "rim": "16", \
            "run_flat": "No",\
            "speed_rating": "V",\
            "width": "205",\
            "xl": "No"\
        }, \
        "name": "Sport Contact 2",\
        "price": "77.80",\
        "sku": "",\
        "url": "http://asdatyres.co.uk"\
    }
    >>> find_mts_stock_code_optimized(product, spider_name='asdatyres.co.uk')
    '2055516VCOSPT2'
    >>> product = { \
        "brand": "Pirelli",  \
        "category": "Premium Brands",  \
        "identifier": "412554",  \
        "image_url": "http://cdn.tyreleader.co.uk/static/img/tyre_small_cp/7013.jpg",  \
        "metadata": { \
            "alternative_speed_rating": "",  \
            "aspect_ratio": "55",  \
            "fitting_method": "Delivered",  \
            "full_tyre_size": "205/55/16/91/V",  \
            "load_rating": "91",  \
            "manufacturer_mark": "", \
            "mts_stock_code": "2055516VPIP7CINT", \
            "rim": "16",  \
            "run_flat": "No", \
            "speed_rating": "V", \
            "width": "205",  \
            "xl": "No" \
        },  \
        "name": "Cinturato P7", \
        "price": "57.69",  \
        "sku": "",  \
        "url": "http://www.tyreleader.co.uk/car-tyres/pirelli/cinturato-p7/205-55-r16-91v-412554" \
    }
    >>> find_mts_stock_code_optimized(product, 'tyreleader.co.uk')
    '2055516VPIP7CINT'
    >>> product = { \
        "brand": "Pirelli",  \
        "category": "Premium Brands",  \
        "identifier": "412554",  \
        "image_url": "http://cdn.tyreleader.co.uk/static/img/tyre_small_cp/7013.jpg",  \
        "metadata": { \
            "alternative_speed_rating": "",  \
            "aspect_ratio": "55",  \
            "fitting_method": "Delivered",  \
            "full_tyre_size": "205/55/16/91/V",  \
            "load_rating": "91",  \
            "manufacturer_mark": "", \
            "mts_stock_code": "2055516VPIP7CINT", \
            "rim": "16",  \
            "run_flat": "No", \
            "speed_rating": "V", \
            "width": "205",  \
            "xl": "No" \
        },  \
        "name": "P7", \
        "price": "57.69",  \
        "sku": "",  \
        "url": "http://www.tyreleader.co.uk/car-tyres/pirelli/cinturato-p7/205-55-r16-91v-412554" \
    }
    >>> find_mts_stock_code_optimized(product, 'tyreleader.co.uk')
    '2055516VPIP7'
    >>> product = {\
        "brand": "Bridgestone",\
        "category": "Premium Brands",\
        "identifier": "1619555HBRER3002RFT",\
        "image_url": "http://www.asdatyres.co.uk/order/tyre_images/Bridgestone/er300.jpg",\
        "metadata": {\
            "alternative_speed_rating": "",\
            "aspect_ratio": "55", \
            "fitting_method": "Fitted",\
            "full_tyre_size": "195/55/16/87/H",\
            "load_rating": "87",\
            "manufacturer_mark": "",\
            "rim": "16",\
            "run_flat": "Yes",\
            "speed_rating": "H",\
            "width": "195",\
            "xl": "No"\
        },\
        "name": "ER300-2",\
        "price": "102.90",\
        "sku": "",\
        "url": "http://asdatyres.co.uk"\
    }
    >>> find_mts_stock_code_optimized(product, 'asdatyres.co.uk')
    '1955516HBRER300R'
    >>> product = {\
        "brand": "Pirelli",\
        "category": "House Brands",\
        "identifier": "pirelli-pzero-rosso-225-45-r17-91-w-mo",\
        "image_url": "http://www.oponeo.co.uk/Temp/pirelli-pzero-rosso-1285-t-f-l125-sk1.png",\
        "metadata": {\
            "alternative_speed_rating": "W",\
            "aspect_ratio": "45",\
            "fitting_method": "Delivered",\
            "full_tyre_size": "225/45/17/91/W",\
            "load_rating": "91",\
            "manufacturer_mark": "MO",\
            "mts_stock_code": "2254517ZPIPZROSS",\
            "rim": "17",\
            "run_flat": "No",\
            "speed_rating": "Z",\
            "width": "225",\
            "xl": "No"\
        },\
        "name": "PZero Rosso",\
        "price": "80",\
        "sku": "",\
        "url": "http://www.oponeo.co.uk/tyre-details/pirelli-pzero-rosso-225-45-r17-91-w"\
    }
    >>> find_mts_stock_code_optimized(product, 'oponeo.co.uk')
    '2254517ZPIROSSMO'
    >>> product = {\
        'brand': u'Pirelli',\
        'category': u'Premium Brands',\
        'identifier': u'100778',\
        'image_url': 'http://www.camskill.co.uk/smsimg/1943/100778--main--1943.jpg',\
        'metadata': {\
            u'alternative_speed_rating': '',\
            u'aspect_ratio': u'55',\
            u'fitting_method': u'Delivered',\
            u'full_tyre_size': u'205/55/16/91/V',\
            u'load_rating': u'91',\
            u'manufacturer_mark': None,\
            u'mts_stock_code': '2055516VPIP7',\
            u'rim': u'16',\
            u'run_flat': u'No',\
            u'speed_rating': 'V',\
            u'width': u'205',\
            u'xl': u'No'\
        },\
        'name': u'Cinturato P7',\
        'price': '61.90',\
        'sku': None,\
        'url': 'http://www.camskill.co.uk/m62b0s3986p100778/Pirelli_Tyres_Car_Pirelli_P7_Cinturato_Pirelli_P_7_-_205_55_R16_91V_%28MO%29_TL_Fuel_Eff_%3A_E_Wet_Grip%3A_B_NoiseClass%3A_2_Noise%3A_70dB'\
    }
    >>> find_mts_stock_code_optimized(product, 'micheldever-camskill.co.uk')
    '2055516VPIP7CINT'
    >>> product = {\
        'brand': u'Michelin',\
        'category': u'Premium Brands',\
        'identifier': u'102543',\
        'image_url': 'http://www.camskill.co.uk/smsimg/1127/102543-108166-main--1127.jpg',\
        'metadata': {\
            u'alternative_speed_rating': '',\
            u'aspect_ratio': u'55',\
            u'fitting_method': u'Delivered',\
            u'full_tyre_size': u'205/55/16/91/V',\
            u'load_rating': u'91',\
            u'manufacturer_mark': None,\
            u'mts_stock_code': '2055516VMIPRHPMO',\
            u'rim': u'16',\
            u'run_flat': u'No',\
            u'speed_rating': 'V',\
            u'width': u'205',\
            u'xl': u'No'\
        },\
        'name': u'Primacy HP',\
        'price': '66.50',\
        'sku': None,\
        'url': 'http://www.camskill.co.uk/m62b0s3986p102543/Michelin_Tyres_Car_Michelin_Primacy_HP_-_205_55_R16_91V_%28MO%29_TL_Fuel_Eff_%3A_C_Wet_Grip%3A_B_NoiseClass%3A_2_Noise%3A_70dB'\
    }
    >>> find_mts_stock_code_optimized(product, 'micheldever-camskill.co.uk')
    '2055516VMIPRIHPA'
    >>> product = {\
        'brand': u'Pirelli',\
        'category': u'Premium Brands',\
        'identifier': u'101375',\
        'image_url': 'http://www.camskill.co.uk/smsimg/1102/101375--main--1102.jpg',\
        'metadata': {\
            u'alternative_speed_rating': 'Y',\
            u'aspect_ratio': u'35',\
            u'fitting_method': u'Delivered',\
            u'full_tyre_size': u'235/35/19/91/Y',\
            u'load_rating': u'91',\
            u'manufacturer_mark': None,\
            u'mts_stock_code': '2353519ZPIPZERO1',\
            u'rim': u'19',\
            u'run_flat': u'No',\
            u'speed_rating': 'Z',\
            u'width': u'235',\
            u'xl': u'Yes'\
        },\
        'name': u'PZero',\
        'price': '156.40',\
        'sku': None,\
        'url': 'http://www.camskill.co.uk/m55b0s24p101375/Pirelli_Tyres_Car_Pirelli_PZero_Pirelli_P_Zero_-_235_35_R19_%2891Y%29_XL_%28L%29_TL_Fuel_Eff_%3A_E_Wet_Grip%3A_A_NoiseClass%3A_2_Noise%3A_72dB'
    }
    >>> find_mts_stock_code_optimized(product, 'micheldever-camskill.co.uk')
    '2353519ZPIPZERO'
    """
    product['name'] = product['name'].strip()
    if product['metadata']['manufacturer_mark'] is None:
        product['metadata']['manufacturer_mark'] = ''
    if ip_code is not None:
        mts_stock_code = find_mts_stock_code_by_ipcode(ip_code)
        if mts_stock_code:
            if log:
                log('MTS matched by IP Code %s: %s' % (ip_code, mts_stock_code))
            return mts_stock_code
    mts_stock_code = find_manually_matched_mts_stock_code_optimized(product, spider_name=spider_name)
    if mts_stock_code:
        if log:
            log('MTS Manually matched: %s' % mts_stock_code)
        return mts_stock_code

    tyres_dict = load_mts_stock_codes_dict()
    metadata = product['metadata']
    product_key = get_mts_stock_key(metadata)
    tyres_list = tyres_dict.get(product_key) or []

    for tyre in tyres_list:
        load_ratings = tyre['Load rating'].split('/')
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed rating'] or metadata['speed_rating'] == tyre['Alt Speed']) and
                  metadata['load_rating'] in load_ratings)

        xl_correct = (metadata['xl'] == "Yes" and tyre['XL'] == "XL") or (metadata['xl'] == "No" and tyre['XL'] == "")
        rf_correct = (metadata['run_flat'] == "Yes" and tyre['Run Flat'] == "RF") or (metadata['run_flat'] == "No" and tyre['Run Flat'] == "")

        brand_correct = is_brand_correct(tyre['Brand'],
                                         product['brand'].lower())
        if search and xl_correct and rf_correct and brand_correct:
            matched = tyre['Pattern'].lower().replace(' ', '') == product['name'].lower().replace(' ', '')
            if matched:
                if log:
                    log('MTS automatically matched: %s' % mts_stock_code)
                return tyre['MTS Stockcode']

    for tyre in tyres_list:
        load_ratings = tyre['Load rating'].split('/')
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed rating'] or metadata['speed_rating'] == tyre['Alt Speed']) and
                  metadata['load_rating'] in load_ratings)

        xl_correct = (metadata['xl'] == "Yes" and tyre['XL'] == "XL") or (metadata['xl'] == "No" and tyre['XL'] == "")
        rf_correct = (metadata['run_flat'] == "Yes" and tyre['Run Flat'] == "RF") or (metadata['run_flat'] == "No" and tyre['Run Flat'] == "")

        brand_correct = is_brand_correct(tyre['Brand'],
                                         product['brand'].lower())
        if search and xl_correct and rf_correct and brand_correct:
            matched = match_name(tyre['Pattern'], product['name']) or match_pattern(tyre['Pattern'], product['name'])
            if matched:
                if log:
                    log('MTS automatically matched: %s' % mts_stock_code)
                return tyre['MTS Stockcode']

    return ''

def find_manually_matched_mts_stock_code_optimized(product, spider_name=None, respect_website=True):
    """
    >>> product = { \
        "brand": "Falken", \
        "category": "House Brands", \
        "identifier": "32846300-Fitted", \
        "image_url": "http://www.blackcircles.com/wso/images/library/obj26189784?view=2885", \
        "metadata": { \
            "alternative_speed_rating": "", \
            "aspect_ratio": "70", \
            "fitting_method": "Fitted", \
            "full_tyre_size": "165/70/14/81/T", \
            "load_rating": "81", \
            "manufacturer_mark": "", \
            "mts_stock_code": "", \
            "rim": "14", \
            "run_flat": "No", \
            "speed_rating": "T", \
            "width": "165", \
            "xl": "No" \
        }, \
        "name": "Sincera SN832 Ecorun", \
        "price": "49.08", \
        "sku": "", \
        "url": "http://www.blackcircles.com/catalogue//falken/sincera-sn832-ecorun/165/70/R14/T/81" \
    }
    >>> find_manually_matched_mts_stock_code_optimized(product, 'blackcircles.com')
    '1657014TBUFA832'
    >>> product = { \
        "brand": "Pirelli",  \
        "category": "Premium Brands",  \
        "identifier": "412554",  \
        "image_url": "http://cdn.tyreleader.co.uk/static/img/tyre_small_cp/7013.jpg",  \
        "metadata": { \
            "alternative_speed_rating": "",  \
            "aspect_ratio": "55",  \
            "fitting_method": "Delivered",  \
            "full_tyre_size": "205/55/16/91/V",  \
            "load_rating": "91",  \
            "manufacturer_mark": "", \
            "mts_stock_code": "2055516VPIP7CINT", \
            "rim": "16",  \
            "run_flat": "No", \
            "speed_rating": "V", \
            "width": "205",  \
            "xl": "No" \
        },  \
        "name": "Cinturato P7", \
        "price": "57.69",  \
        "sku": "",  \
        "url": "http://www.tyreleader.co.uk/car-tyres/pirelli/cinturato-p7/205-55-r16-91v-412554" \
    }
    >>> find_manually_matched_mts_stock_code_optimized(product, 'tyreleader.co.uk')
    '2055516VPIP7CINT'
    >>> product = { \
        "brand": "Pirelli",  \
        "category": "Premium Brands",  \
        "identifier": "412554",  \
        "image_url": "http://cdn.tyreleader.co.uk/static/img/tyre_small_cp/7013.jpg",  \
        "metadata": { \
            "alternative_speed_rating": "",  \
            "aspect_ratio": "55",  \
            "fitting_method": "Delivered",  \
            "full_tyre_size": "205/55/16/91/V",  \
            "load_rating": "91",  \
            "manufacturer_mark": "", \
            "mts_stock_code": "2055516VPIP7CINT", \
            "rim": "16",  \
            "run_flat": "No", \
            "speed_rating": "V", \
            "width": "205",  \
            "xl": "No" \
        },  \
        "name": "P7", \
        "price": "57.69",  \
        "sku": "",  \
        "url": "http://www.tyreleader.co.uk/car-tyres/pirelli/cinturato-p7/205-55-r16-91v-412554" \
    }
    >>> find_manually_matched_mts_stock_code_optimized(product, 'tyreleader.co.uk')
    ''
    """
    if not spider_name and respect_website:
        return ''

    product['name'] = product['name'].strip()

    tyres_dict = load_manual_mts_stock_codes_dict()

    metadata = product['metadata']


    product_key = get_manual_mts_stock_key(spider_name, metadata)
    tyres_list = tyres_dict.get(product_key) or []


    # first loop check for exact match
    for tyre in tyres_list:
        if tyre['Website'] != spider_name and respect_website:
            continue
        load_ratings = tyre['Load rating'].split('/')
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed Rating'] or metadata['speed_rating'] == tyre['Alternative speed rating']) and
                  metadata['load_rating'] in load_ratings)

        if not tyre['XL']:
            tyre['XL'] = 'No'
        if tyre['XL'] == 'XL':
            tyre['XL'] = 'Yes'
        if not tyre['Run Flat']:
            tyre['Run Flat'] = 'No'
        if tyre['Run Flat'] == 'RFT':
            tyre['Run Flat'] = 'Yes'

        xl_correct = (metadata['xl'] == tyre['XL'])
        rf_correct = (metadata['run_flat'] == tyre['Run Flat'])
        mf_mark_correct = (metadata['manufacturer_mark'] == tyre['Manufacturer mark'])

        brand_correct = is_brand_correct(tyre['Brand'],
                                         product['brand'].lower())
        if search and xl_correct and rf_correct and brand_correct and mf_mark_correct:
            matched = tyre['Pattern'].lower().replace(' ', '') == product['name'].lower().replace(' ', '')
            if matched:
                if tyre['MTS Stock Code']:
                    return tyre['MTS Stock Code']

    return ''

def is_product_correct_optimized(product):
    """
    >>> from decimal import Decimal
    >>> product = {'brand': u'Kumho',\
    'category': u'House Brands',\
    'identifier': u'11179484-Delivered',\
    'image_url': 'http://www.blackcircles.com/wso/images/library/obj16003867?view=2885',\
    'name': u'Ecsta SPT KU31',\
    'price': Decimal('51.804'),\
    'sku': u'2055516v',\
    'url': 'http://www.blackcircles.com/kumho/ku31/205/55/R16/V/91',\
    'metadata': {'alternative_speed_rating': '',\
    'aspect_ratio': '55',\
    'fitting_method': 'Delivered',\
    'full_tyre_size': u'205/55/16/91/V',\
    'load_rating': u'91',\
    'manufacturer_mark': '',\
    'mts_stock_code': '',\
    'rim': '16',\
    'run_flat': 'No',\
    'speed_rating': u'V',\
    'width': '205',\
    'xl': 'No'}}
    >>> is_product_correct_optimized(product)
    True
    """

    metadata = product['metadata']
    tyres_dict = load_mts_stock_codes_dict()
    product_key = get_mts_stock_key(metadata)
    tyres_list = tyres_dict.get(product_key) or []
    for tyre in tyres_list:
        load_ratings = tyre['Load rating'].split('/')
        search = (metadata['width'] == tyre['Width'] and
                  metadata['aspect_ratio'] == tyre['Aspect Ratio'] and
                  metadata['rim'] == tyre['Rim'] and
                  (metadata['speed_rating'] == tyre['Speed rating'] or metadata['speed_rating'] == tyre['Alt Speed']) and
                  metadata['load_rating'] in load_ratings)

        xl_correct = (metadata['xl'] == "Yes" and tyre['XL'] == "XL") or (metadata['xl'] == "No" and tyre['XL'] == "")
        rf_correct = (metadata['run_flat'] == "Yes" and tyre['Run Flat'] == "RF") or (metadata['run_flat'] == "No" and tyre['Run Flat'] == "")

        brand_correct = is_brand_correct(tyre['Brand'], product['brand'].lower())
        # collect all Apollo tyres
        brand_is_apollo = product['brand'].lower() == 'apollo' or product['brand'].lower() == 'apollo tyres' or product['brand'].lower() == 'apollo tyre'
        brand_correct = brand_correct or brand_is_apollo
        if search and xl_correct and rf_correct and brand_correct:
            return True

    return False
