# -*- coding: utf-8 -*-

import os
from product_spiders.spiders.eservicegroup_uk.eglobalcentral import EGlobalCentral


HERE = os.path.abspath(os.path.dirname(__file__))


class EGlobalCentralBeSpider(EGlobalCentral):
    name = "eglobalcentral_com_es"
    allowed_domains = ["eglobalcentral.com.es", "148.251.79.44", "searchanise.com"]
    search_url = 'http://www.eglobalcentral.com.es/product?subcats=Y&status=A&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&hint_q=B%C3%BAscar%20art%C3%ADculo&items_per_page=200'
    data_file = os.path.join(HERE, 'eglobal.csv')
    searchanise_api = '3t3g6u4D6Q'
