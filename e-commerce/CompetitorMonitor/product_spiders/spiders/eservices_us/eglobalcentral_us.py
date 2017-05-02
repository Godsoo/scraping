# -*- coding: utf-8 -*-

import os
from product_spiders.spiders.eservicegroup_uk.eglobalcentral import EGlobalCentral


HERE = os.path.abspath(os.path.dirname(__file__))


class EGlobalCentralUSSpider(EGlobalCentral):
    name = "eglobalcentral_us"
    allowed_domains = ["eglobalcentral.com", "148.251.79.44", "searchanise.com"]
    search_url = 'http://www.eglobalcentral.com/product/?i=Y&items_per_page=200&sort_by=product&sort_order=asc'
    data_file = os.path.join(HERE, 'eglobal.csv')
    searchanise_api = '2m3Q3A3C0W'
