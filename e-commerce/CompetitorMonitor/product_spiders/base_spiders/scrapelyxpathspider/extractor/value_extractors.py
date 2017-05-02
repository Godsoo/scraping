# -*- coding: utf-8 -*-
from w3lib.url import safe_download_url

from scrapely.extractors import extract_price, extract_number, extract_image_url, htmlregion, \
    text as scrapely_extract_text


def extract_text(value):
    res = scrapely_extract_text(htmlregion(value))
    return res


def extract_stock(value, default=True):
    """
    Extracts stock value from text
    :param value: original text
    :param default: default value if can't determine from text
    :return: True if in stock, False otherwise
    """
    in_stock_txt = ['in stock', 'instock', 'in-stock']
    out_stock_txt = ['out stock', 'out of stock', 'discontinued']

    if value.lower() in in_stock_txt:
        return True
    if value.lower() in out_stock_txt:
        return False
    return default

EXTRACTOR_MAPPING = {
    'text': extract_text,
    'number': extract_number,
    'price': extract_price,
    'url': safe_download_url,
    'image_url': extract_image_url,
    'stock_number': extract_number,
    'stock_text': extract_stock
}


def get_extractor_function(extr_name):
    if extr_name not in EXTRACTOR_MAPPING:
        raise ValueError("Wrong extractor type: %s" % extr_name)
    return EXTRACTOR_MAPPING[extr_name]