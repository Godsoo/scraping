# -*- coding: utf-8 -*-

import os
from product_spiders.spiders.eservicegroup_uk.eglobalcentral import EGlobalCentral


HERE = os.path.abspath(os.path.dirname(__file__))


class EGlobalCentralFrSpider(EGlobalCentral):
    name = 'eglobalcentral_fr'
    allowed_domains = ['eglobalcentral.fr', '148.251.79.44', 'searchanise.com']
    search_url = 'http://www.eglobalcentral.fr/product?subcats=Y&status=A&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&hint_q=Rechercher%20des%20produits&items_per_page=200'
    data_file = os.path.join(HERE, 'eglobal.csv')
    searchanise_api = '6u5o3O0t5H'
