# -*- coding: utf-8 -*-

import os
from product_spiders.spiders.eservicegroup_uk.eglobalcentral import EGlobalCentral


HERE = os.path.abspath(os.path.dirname(__file__))


class EGlobalCentralSpider(EGlobalCentral):
    name = "eglobalcentral_pl"
    allowed_domains = ["eglobalcentral.pl", "148.251.79.44", "searchanise.com"]
    search_url = 'http://www.eglobalcentral.pl/product?subcats=Y&status=A&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&hint_q=Wyszukaj%20produkty&items_per_page=100'
    data_file = os.path.join(HERE, 'eglobal.csv')
    searchanise_api = '2N3x0P1I6j'
    use_searchanise = True
