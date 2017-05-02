# -*- coding: utf-8 -*-
from product_spiders.custom_crawl_methods.bigsitemethod import make_bigsitemethod_spider, check_fits_to_bigsitemethod, \
    PARAMS
CRAWL_METHODS = {
    'BigSiteMethod': make_bigsitemethod_spider
}

CRAWL_METHOD_FIT_CHECK_FUNCS = {
    'BigSiteMethod': check_fits_to_bigsitemethod
}

CRAWL_METHOD_PARAMS = {
    'BigSiteMethod': PARAMS
}