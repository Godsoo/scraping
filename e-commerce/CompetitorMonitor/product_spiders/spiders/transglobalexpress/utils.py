# -*- coding: utf-8 -*-


def extract_brand(name):
    brands = ['DPD', 'TNT', 'UPS', 'FX', 'Parcelforce']
    brand = ''
    for b in brands:
        if b.upper() in name.upper():
            brand = b
            break
    return brand
