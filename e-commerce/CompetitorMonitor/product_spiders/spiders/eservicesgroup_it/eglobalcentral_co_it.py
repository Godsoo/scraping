# -*- coding: utf-8 -*-

import os
from product_spiders.spiders.eservicegroup_uk.eglobalcentral import EGlobalCentral


HERE = os.path.abspath(os.path.dirname(__file__))


class EGlobalCentralITSpider(EGlobalCentral):
    name = "eglobalcentral_co_it"
    allowed_domains = ["eglobalcentral.co.it", "148.251.79.44", "searchanise.com"]
    search_url = 'http://www.eglobalcentral.co.it/product?subcats=Y&status=A&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&hint_q=Ricerca%20prodotti&items_per_page=200'
    data_file = os.path.join(HERE, 'eglobal.csv')
    searchanise_api = '3d2c9D8P3q'
